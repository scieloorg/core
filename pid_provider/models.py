import hashlib
import logging
import os
from datetime import datetime
from http import HTTPStatus
from shutil import copyfile
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from pid_provider import exceptions, v3_gen, xml_sps_adapter
from xmlsps.xml_sps_lib import XMLWithPre
from xmlsps.models import XMLIssue, XMLJournal, XMLSPS


LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def utcnow():
    return datetime.utcnow()
    # return datetime.utcnow().isoformat().replace("T", " ") + "Z"


class PidProviderConfig(CommonControlField):
    """
    Tem função de guardar XML que falhou no registro
    """

    pid_provider_api_post_xml = models.TextField(
        _("XML Post URI"), null=True, blank=True
    )
    pid_provider_api_get_token = models.TextField(
        _("Get Token URI"), null=True, blank=True
    )
    timeout = models.IntegerField(_("Timeout"), null=True, blank=True)
    api_username = models.TextField(_("API Username"), null=True, blank=True)
    api_password = models.TextField(_("API Password"), null=True, blank=True)

    def __unicode__(self):
        return f"{self.pid_provider_api_post_xml}"

    def __str__(self):
        return f"{self.pid_provider_api_post_xml}"

    @classmethod
    def get_or_create(
        cls,
        creator=None,
        pid_provider_api_post_xml=None,
        pid_provider_api_get_token=None,
        api_username=None,
        api_password=None,
        timeout=None,
    ):
        obj = cls.objects.first()
        if obj is None:
            obj = cls()
            obj.pid_provider_api_post_xml = pid_provider_api_post_xml
            obj.pid_provider_api_get_token = pid_provider_api_get_token
            obj.api_username = api_username
            obj.api_password = api_password
            obj.timeout = timeout
            obj.creator = creator
            obj.save()
        return obj

    panels = [
        FieldPanel("pid_provider_api_post_xml"),
        FieldPanel("pid_provider_api_get_token"),
        FieldPanel("api_username"),
        FieldPanel("api_password"),
        FieldPanel("timeout"),
    ]

    base_form_class = CoreAdminModelForm


class PidProviderBadRequest(CommonControlField):
    """
    Tem função de guardar XML que falhou no registro
    """

    basename = models.TextField(_("Basename"), null=True, blank=True)
    finger_print = models.CharField(max_length=65, null=True, blank=True)
    error_type = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    xml = models.FileField(upload_to="bad_request")

    class Meta:

        indexes = [
            models.Index(fields=["basename"]),
            models.Index(fields=["finger_print"]),
            models.Index(fields=["error_type"]),
            models.Index(fields=["error_message"]),
        ]

    def __unicode__(self):
        return f"{self.basename} {self.error_type}"

    def __str__(self):
        return f"{self.basename} {self.error_type}"

    @property
    def data(self):
        return {
            "error_type": self.error_type,
            "error_message": self.error_message,
            "id": self.finger_print,
            "filename": self.basename,
        }

    @classmethod
    def get_or_create(cls, creator, basename, exception, xml_adapter):
        finger_print = xml_adapter.finger_print

        try:
            obj = cls.objects.get(finger_print=finger_print)
        except cls.DoesNotExist:
            obj = cls()
            obj.finger_print = finger_print

        obj.xml = ContentFile(xml_adapter.tostring(), name=finger_print + ".xml")
        obj.basename = basename
        obj.error_type = str(type(exception))
        obj.error_message = str(exception)
        obj.creator = creator
        obj.save()
        return obj

    panels = [
        FieldPanel("basename"),
        FieldPanel("xml"),
        FieldPanel("error_type"),
        FieldPanel("error_message"),
    ]

    base_form_class = CoreAdminModelForm


def xml_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f"xml_pid_provider/{instance.finger_print[-1]}/{instance.finger_print[-2]}/{instance.finger_print}/{filename}"


class XMLVersion(CommonControlField):
    """
    Tem função de guardar a versão do XML
    """

    pid_provider_xml = models.ForeignKey(
        "PidProviderXML", on_delete=models.SET_NULL, null=True, blank=True
    )
    file = models.FileField(upload_to=xml_directory_path, null=True, blank=True)
    finger_print = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["finger_print"]),
            models.Index(fields=["pid_provider_xml"]),
        ]

    def __str__(self):
        return self.finger_print

    @classmethod
    def create(
        cls,
        creator,
        pid_provider_xml,
        pkg_name=None,
        finger_print=None,
        zip_xml_content=None,
    ):
        logging.info(f"XMLVersion.create({pkg_name})")
        obj = cls()
        obj.finger_print = finger_print
        obj.pkg_name = pkg_name
        obj.save_file(pkg_name + ".zip", zip_xml_content)
        obj.creator = creator
        obj.created = utcnow()
        obj.save()

        # salvar pid_provider_xml e salvar self para evitar exceção
        obj.pid_provider_xml = pid_provider_xml
        obj.save()
        return obj

    def save_file(self, name, content):
        self.file.save(name, ContentFile(content))

    @property
    def xml_with_pre(self):
        try:
            for item in XMLWithPre.create(path=self.file.path):
                yield item
        except Exception as e:
            raise exceptions.PidProviderXMLWithPreError(
                _("Unable to get xml with pre (PidProviderXML) {}: {} {}").format(
                    self.pkg_name, type(e), e
                )
            )


class XMLRelatedItem(CommonControlField):
    """
    Tem função de guardar os relacionamentos entre outro Documento (Artigo)
    Tem objetivo de identificar o Documento (Artigo)
    """

    main_doi = models.TextField(_("DOI"), null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["main_doi"]),
        ]

    def __str__(self):
        return self.main_doi

    @classmethod
    def get_or_create(cls, main_doi, creator=None):
        try:
            return cls.objects.get(main_doi=main_doi)
        except cls.DoesNotExist:
            obj = cls()
            obj.main_doi = main_doi
            obj.creator = creator
            obj.created = utcnow()
            obj.save()
            return obj


class PidChange(CommonControlField):
    pid_type = models.CharField(_("PID type"), max_length=23, null=True, blank=True)
    old = models.CharField(_("PID old"), max_length=23, null=True, blank=True)
    new = models.CharField(_("PID new"), max_length=23, null=True, blank=True)
    version = models.ForeignKey(XMLVersion, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [
            models.Index(fields=["old"]),
            models.Index(fields=["new"]),
            models.Index(fields=["pid_type"]),
            models.Index(fields=["version"]),
        ]

    def __str__(self):
        return str((self.pid_v3, self.pid_v2, self.aop_pid))

    @classmethod
    def get_or_create(cls, pid_type, old, new, version, user):
        try:
            return cls.objects.get(
                pid_type=pid_type, old=old, new=new, version=version,
            )
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user
            obj.pid_type = pid_type
            obj.old = old
            obj.new = new
            obj.version = version
            obj.save()
            return obj


class PidProviderXML(CommonControlField):
    """
    Tem responsabilidade de garantir a atribuição do PID da versão 3,
    armazenando dados chaves que garantem a identificação do XML
    """

    journal = models.ForeignKey(
        XMLJournal, on_delete=models.SET_NULL, null=True, blank=True
    )
    issue = models.ForeignKey(
        XMLIssue, on_delete=models.SET_NULL, null=True, blank=True
    )
    related_items = models.ManyToManyField(XMLRelatedItem)
    current_version = models.ForeignKey(
        XMLVersion, on_delete=models.SET_NULL, null=True, blank=True
    )
    current_xml = models.ForeignKey(
        XMLSPS, on_delete=models.SET_NULL, null=True, blank=True
    )

    pkg_name = models.TextField(_("Package name"), null=True, blank=True)
    v3 = models.CharField(_("v3"), max_length=23, null=True, blank=True)
    v2 = models.CharField(_("v2"), max_length=23, null=True, blank=True)
    aop_pid = models.CharField(_("AOP PID"), max_length=23, null=True, blank=True)

    elocation_id = models.TextField(_("elocation id"), null=True, blank=True)
    fpage = models.CharField(_("fpage"), max_length=10, null=True, blank=True)
    fpage_seq = models.CharField(_("fpage_seq"), max_length=10, null=True, blank=True)
    lpage = models.CharField(_("lpage"), max_length=10, null=True, blank=True)
    article_pub_year = models.CharField(
        _("Document Publication Year"), max_length=4, null=True, blank=True
    )
    main_toc_section = models.TextField(_("main_toc_section"), null=True, blank=True)
    main_doi = models.TextField(_("DOI"), null=True, blank=True)

    z_article_titles_texts = models.CharField(
        _("article_titles_texts"), max_length=64, null=True, blank=True
    )
    z_surnames = models.CharField(_("surnames"), max_length=64, null=True, blank=True)
    z_collab = models.CharField(_("collab"), max_length=64, null=True, blank=True)
    z_links = models.CharField(_("links"), max_length=64, null=True, blank=True)
    z_partial_body = models.CharField(
        _("partial_body"), max_length=64, null=True, blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["pkg_name"]),
            models.Index(fields=["v3"]),
            models.Index(fields=["journal"]),
            models.Index(fields=["issue"]),
            models.Index(fields=["elocation_id"]),
            models.Index(fields=["fpage"]),
            models.Index(fields=["fpage_seq"]),
            models.Index(fields=["lpage"]),
            models.Index(fields=["article_pub_year"]),
            models.Index(fields=["main_doi"]),
            models.Index(fields=["z_article_titles_texts"]),
            models.Index(fields=["z_surnames"]),
            models.Index(fields=["z_collab"]),
            models.Index(fields=["z_links"]),
            models.Index(fields=["z_partial_body"]),
        ]

    def __str__(self):
        return self.pkg_name or self.v3 or "PidProviderXML sem ID"

    @property
    def data(self):
        _data = {
            "v3": self.v3,
            "v2": self.v2,
            "aop_pid": self.aop_pid,
            "pkg_name": self.pkg_name,
            "created": self.created and self.created.isoformat(),
            "updated": self.updated and self.updated.isoformat(),
            "record_status": "updated" if self.updated else "created",
        }
        return _data

    @classmethod
    def get_xml_with_pre(cls, v3):
        try:
            return cls.objects.get(v3=v3).xml_with_pre
        except:
            return None

    @property
    def xml_with_pre(self):
        return self.current_version and self.current_version.xml_with_pre

    @property
    def is_aop(self):
        return self.issue is None

    def set_current_version(self, creator, pkg_name, xml_adapter, user):
        finger_print = xml_adapter.finger_print
        if (
            not self.current_version
            or self.current_version.finger_print != finger_print
            or not self.current_xml
        ):
            self.current_version = XMLVersion.create(
                creator=creator,
                pid_provider_xml=self,
                pkg_name=pkg_name,
                finger_print=finger_print,
                zip_xml_content=xml_adapter.xml_with_pre.get_zip_content(pkg_name+".xml"),
            )
            self.current_xml = XMLSPS.create_or_update(
                pid_v3=self.v3,
                pid_v2=self.v2,
                aop_pid=self.aop_pid,
                xml=xml_adapter.tostring(),
                xml_journal=self.journal,
                xml_issue=self.issue,
                user=user,
            )

    @classmethod
    def register(
        cls,
        xml_with_pre,
        filename,
        user,
    ):
        """
        Evaluate the XML data and returns corresponding PID v3, v2, aop_pid

        Parameters
        ----------
        xml : XMLWithPre
        filename : str
        user : User

        Returns
        -------
            {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_uri": self.xml_uri,
                "article": self.article,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
                "xml_changed": boolean,
                "record_status": created | updated | retrieved
            }
            or
            {
                "error_type": self.error_type,
                "error_message": self.error_message,
                "id": self.finger_print,
                "filename": self.name,
            }

        """
        try:
            logging.info(f"PidProviderXML.register ....  {filename}")
            pkg_name, ext = os.path.splitext(os.path.basename(filename))

            # adaptador do xml with pre
            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)

            # consulta se documento já está registrado
            registered = cls._query_document(xml_adapter)

            if registered and registered.is_equal_to(xml_adapter):
                # retorna item registrado
                return registered.data

            # analisa se aceita ou rejeita registro
            cls.evaluate_registration(xml_adapter, registered)

            # verfica os PIDs encontrados no XML / atualiza-os se necessário
            changed_pids = cls._complete_pids(xml_adapter, registered)

            registered = cls._save(
                registered,
                xml_adapter,
                user,
                pkg_name,
                changed_pids,
            )


            data = registered.data.copy()
            data["xml_changed"] = bool(changed_pids)
            return data

        except (
            exceptions.ForbiddenPidProviderXMLRegistrationError,
            exceptions.NotEnoughParametersToGetDocumentRecordError,
            exceptions.QueryDocumentMultipleObjectsReturnedError,
        ) as e:
            bad_request = PidProviderBadRequest.get_or_create(
                user,
                filename,
                e,
                xml_adapter,
            )
            return bad_request.data

    def _register_pid_changes(self, changed_pids, user):
        # requires registered.current_version is set

        if not self.current_version:
            raise ValueError("PidProviderXML._register_pid_changes requires current_version is set")
        for change_args in changed_pids:
            if change_args["old"]:
                # somente registra as mudanças de um old não vazio
                change_args["user"] = user
                change_args["version"] = self.current_version
                change = PidChange.get_or_create(**change_args)

    @classmethod
    def _save(
        cls,
        registered,
        xml_adapter,
        user,
        pkg_name,
        changed_pids,
    ):
        if registered:
            registered.updated_by = user
            registered.updated = utcnow()
        else:
            registered = cls()
            registered.creator = user
            registered.created = utcnow()
            registered.save()

        registered._add_data(xml_adapter, user, pkg_name)

        registered.set_current_version(
            creator=user,
            pkg_name=pkg_name,
            xml_adapter=xml_adapter,
            user=user,
        )
        registered.save()

        registered._register_pid_changes(changed_pids, user)

        return registered

    @classmethod
    def evaluate_registration(cls, xml_adapter, registered):
        """
        XML é versão AOP, mas
        documento está registrado com versão VoR (fascículo),
        então, recusar o registro,
        pois está tentando registrar uma versão desatualizada
        """
        logging.info("PidProviderXML.evaluate_registration")
        if xml_adapter.is_aop and registered and not registered.is_aop:
            raise exceptions.ForbiddenPidProviderXMLRegistrationError(
                _(
                    "The XML content is an ahead of print version "
                    "but the document {} is already published in an issue"
                ).format(registered)
            )
        return True

    def is_equal_to(self, xml_adapter):
        return bool(
            self.current_version
            and self.current_version.finger_print == xml_adapter.finger_print
        )

    @classmethod
    def get_registered(cls, xml_with_pre):
        """
        Get registered

        Parameters
        ----------
        xml_with_pre : XMLWithPre

        Returns
        -------
            None
            or
            {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_uri": self.xml_uri,
                "article": self.article,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
            }
            or
            {"error_msg": str(e), "error_type": str(type(e))}
        """
        xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
        try:
            registered = cls._query_document(xml_adapter)
        except (
            exceptions.NotEnoughParametersToGetDocumentRecordError,
            exceptions.QueryDocumentMultipleObjectsReturnedError,
        ) as e:
            logging.exception(e)
            return {"error_msg": str(e), "error_type": str(type(e))}
        if registered:
            return registered.data

    @classmethod
    def _query_document(cls, xml_adapter):
        """
        Query document

        Arguments
        ---------
        xml_adapter : PidProviderXMLAdapter

        Returns
        -------
        None or PidProviderXML

        Raises
        ------
        exceptions.QueryDocumentMultipleObjectsReturnedError
        exceptions.NotEnoughParametersToGetDocumentRecordError
        """
        LOGGER.info("_query_document")
        items = xml_adapter.query_list
        for params in items:
            cls.validate_query_params(params)

            try:
                return cls.objects.get(**params)
            except cls.DoesNotExist:
                continue
            except cls.MultipleObjectsReturned as e:
                # seria inesperado já que os dados informados devem encontrar
                # ocorrência única ou None
                logging.info(f"params={params} | e={e}")
                raise exceptions.QueryDocumentMultipleObjectsReturnedError(
                    _("Found more than one document matching to {}").format(params)
                )

    def _add_data(self, xml_adapter, user, pkg_name):
        logging.info(f"PidProviderXML._add_data {pkg_name}")
        self.pkg_name = pkg_name
        self.article_pub_year = xml_adapter.article_pub_year
        self.v3 = xml_adapter.v3
        self.v2 = xml_adapter.v2
        self.aop_pid = xml_adapter.aop_pid

        self.fpage = xml_adapter.fpage
        self.fpage_seq = xml_adapter.fpage_seq
        self.lpage = xml_adapter.lpage

        self.main_doi = xml_adapter.main_doi
        self.main_toc_section = xml_adapter.main_toc_section
        self.elocation_id = xml_adapter.elocation_id

        self.z_article_titles_texts = xml_adapter.z_article_titles_texts
        self.z_surnames = xml_adapter.z_surnames
        self.z_collab = xml_adapter.z_collab
        self.z_links = xml_adapter.z_links
        self.z_partial_body = xml_adapter.z_partial_body

        self.journal = XMLJournal.get_or_create(
            xml_adapter.journal_issn_electronic,
            xml_adapter.journal_issn_print,
        )
        self.issue = None
        if xml_adapter.volume or xml_adapter.number or xml_adapter.suppl:
            self.issue = XMLIssue.get_or_create(
                self.journal,
                xml_adapter.volume,
                xml_adapter.number,
                xml_adapter.suppl,
                xml_adapter.pub_year,
            )

        for related in xml_adapter.related_items:
            self._add_related_item(related["href"], user)

    def _add_related_item(self, main_doi, creator):
        self.related_items.add(XMLRelatedItem.get_or_create(main_doi, creator))

    @classmethod
    def _get_unique_v3(cls):
        """
        Generate v3 and return it only if it is new

        Returns
        -------
            str
        """
        while True:
            generated = v3_gen.generates()
            if not cls._is_registered_pid(v3=generated):
                return generated

    @classmethod
    def _is_registered_pid(cls, v2=None, v3=None, aop_pid=None):
        if v3:
            kwargs = {"v3": v3}
        elif v2:
            kwargs = {"v2": v2}
        elif aop_pid:
            kwargs = {"aop_pid": aop_pid}

        if kwargs:
            try:
                found = cls.objects.filter(**kwargs)[0]
            except IndexError:
                return False
            else:
                return True

    @classmethod
    def _v2_generates(cls, xml_adapter):
        # '2022-10-19T13:51:33.830085'
        h = utcnow()
        mm = str(h.month).zfill(2)
        dd = str(h.day).zfill(2)
        nnnnn = str(h.timestamp()).split(".")[0][-5:]
        return f"{xml_adapter.v2_prefix}{mm}{dd}{nnnnn}"

    @classmethod
    def _get_unique_v2(cls, xml_adapter):
        """
        Generate v2 and return it only if it is new

        Returns
        -------
            str
        """
        while True:
            generated = cls._v2_generates(xml_adapter)
            if not cls._is_registered_pid(v2=generated):
                return generated

    @classmethod
    def _complete_pids(cls, xml_adapter, registered):
        """
        Update `xml_adapter` pids with `registered` pids or
        create `xml_adapter` pids

        Parameters
        ----------
        xml_adapter: PidProviderXMLAdapter
        registered: XMLArticle

        Returns
        -------
        bool

        """
        before = dict(
            pid_v3=xml_adapter.v3,
            pid_v2=xml_adapter.v2,
            aop_pid=xml_adapter.aop_pid,
        )

        # adiciona os pids faltantes aos dados de entrada
        cls._add_pid_v3(xml_adapter, registered)
        cls._add_pid_v2(xml_adapter, registered)
        cls._add_aop_pid(xml_adapter, registered)

        after = dict(
            pid_v3=xml_adapter.v3,
            pid_v2=xml_adapter.v2,
            aop_pid=xml_adapter.aop_pid,
        )

        LOGGER.info("%s %s" % (before, after))

        changes = []
        for k, v in before.items():
            if v != after[k]:
                changes.append(dict(
                    pid_type=k,
                    old=v,
                    new=after[k],
                ))
        return changes

    @classmethod
    def _is_valid_pid(cls, value):
        return bool(value and len(value) == 23)

    @classmethod
    def _add_pid_v3(cls, xml_adapter, registered):
        """
        Atribui v3 ao xml_adapter,
        recuperando do registered ou obtendo um v3 inédito

        Arguments
        ---------
        xml_adapter: PidProviderXMLAdapter
        registered: XMLArticle
        """
        if registered:
            # recupera do registrado
            xml_adapter.v3 = registered.v3
        else:
            # se v3 de xml está ausente ou já está registrado para outro xml
            if not cls._is_valid_pid(xml_adapter.v3) or cls._is_registered_pid(
                v3=xml_adapter.v3
            ):
                # obtém um v3 inédito
                xml_adapter.v3 = cls._get_unique_v3()

    @classmethod
    def _add_aop_pid(cls, xml_adapter, registered):
        """
        Atribui aop_pid ao xml_adapter, recuperando do registered, se existir

        Arguments
        ---------
        xml_adapter: PidProviderXMLAdapter
        registered: XMLArticle
        """
        if registered and registered.aop_pid:
            xml_adapter.aop_pid = registered.aop_pid

    @classmethod
    def _add_pid_v2(cls, xml_adapter, registered):
        """
        Adiciona ou atualiza a xml_adapter, v2 recuperado de registered ou gerado

        Arguments
        ---------
        xml_adapter: PidProviderXMLAdapter
        registered: XMLArticle

        """
        if registered and registered.v2 and xml_adapter.v2 != registered.v2:
            xml_adapter.v2 = registered.v2
        if not cls._is_valid_pid(xml_adapter.v2):
            xml_adapter.v2 = cls._get_unique_v2(xml_adapter)

    @classmethod
    def validate_query_params(cls, query_params):
        """
        Validate query parameters

        Arguments
        ---------
        filter_by_issue: bool
        aop_version: bool

        Returns
        -------
        bool
        """
        _params = query_params
        if not any(
            [
                _params.get("journal__issn_print"),
                _params.get("journal__issn_electronic"),
            ]
        ):
            raise exceptions.NotEnoughParametersToGetDocumentRecordError(
                _("No attribute enough for disambiguations {}").format(
                    _params,
                )
            )

        if not any(
            [
                _params.get("article_pub_year"),
                _params.get("issue__pub_year"),
            ]
        ):
            raise exceptions.NotEnoughParametersToGetDocumentRecordError(
                _("No attribute enough for disambiguations {}").format(
                    _params,
                )
            )

        if any(
            [
                _params.get("main_doi"),
                _params.get("fpage"),
                _params.get("elocation_id"),
            ]
        ):
            return True

        if not any(
            [
                _params.get("z_surnames"),
                _params.get("z_collab"),
                _params.get("z_links"),
                _params.get("pkg_name"),
            ]
        ):
            raise exceptions.NotEnoughParametersToGetDocumentRecordError(
                _("No attribute enough for disambiguations {}").format(
                    _params,
                )
            )
        return True
