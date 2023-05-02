import hashlib
import logging
import os
from datetime import datetime
from http import HTTPStatus
from shutil import copyfile

from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel

from article.models import Article
from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from files_storage.exceptions import PutXMLContentError
from files_storage.models import MinioFile
from pid_provider import exceptions, v3_gen, xml_sps_adapter
from xmlsps.xml_sps_lib import get_xml_with_pre_from_uri

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def utcnow():
    return datetime.utcnow()
    # return datetime.utcnow().isoformat().replace("T", " ") + "Z"


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
            "basename": self.basename,
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


class XMLJournal(models.Model):
    """
    Tem função de guardar os dados de Journal encontrados no XML
    Tem objetivo de identificar o Documento (Artigo)
    """

    issn_electronic = models.CharField(
        _("issn_epub"), max_length=9, null=True, blank=True
    )
    issn_print = models.CharField(_("issn_ppub"), max_length=9, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["issn_electronic"]),
            models.Index(fields=["issn_print"]),
        ]

    def __str__(self):
        return f"{self.issn_electronic} {self.issn_print}"

    @classmethod
    def get_or_create(cls, issn_electronic, issn_print):
        try:
            return cls.objects.get(
                issn_electronic=issn_electronic,
                issn_print=issn_print,
            )
        except cls.DoesNotExist:
            journal = cls()
            journal.issn_electronic = issn_electronic
            journal.issn_print = issn_print
            journal.save()
            return journal


class XMLIssue(models.Model):
    """
    Tem função de guardar os dados de Issue encontrados no XML
    Tem objetivo de identificar o Documento (Artigo)
    """

    journal = models.ForeignKey(
        XMLJournal, on_delete=models.SET_NULL, null=True, blank=True
    )
    pub_year = models.CharField(_("pub_year"), max_length=4, null=True, blank=True)
    volume = models.CharField(_("volume"), max_length=10, null=True, blank=True)
    number = models.CharField(_("number"), max_length=10, null=True, blank=True)
    suppl = models.CharField(_("suppl"), max_length=10, null=True, blank=True)

    class Meta:
        unique_together = [
            ["journal", "pub_year", "volume", "number", "suppl"],
        ]
        indexes = [
            models.Index(fields=["journal"]),
            models.Index(fields=["volume"]),
            models.Index(fields=["number"]),
            models.Index(fields=["suppl"]),
            models.Index(fields=["pub_year"]),
        ]

    def __str__(self):
        return (
            f'{self.journal} {self.volume or ""} {self.number or ""} {self.suppl or ""}'
        )

    @classmethod
    def get_or_create(cls, journal, volume, number, suppl, pub_year):
        try:
            return cls.objects.get(
                journal=journal,
                volume=volume,
                number=number,
                suppl=suppl,
                pub_year=pub_year,
            )
        except cls.DoesNotExist:
            issue = cls()
            issue.journal = journal
            issue.volume = volume
            issue.number = number
            issue.suppl = suppl
            issue.pub_year = pub_year
            issue.save()
            return issue


class SyncFailure(CommonControlField):
    message = models.CharField(_("Message"), max_length=255, null=True, blank=True)
    exception_type = models.CharField(
        _("Exception Type"), max_length=255, null=True, blank=True
    )
    exception_msg = models.CharField(
        _("Exception Msg"), max_length=555, null=True, blank=True
    )
    traceback = models.JSONField(null=True, blank=True)

    @classmethod
    def create(cls, message, e, creator):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        obj = cls()
        obj.message = message
        obj.exception_msg = str(e)[:555]
        obj.traceback = [str(item) for item in traceback.extract_tb(exc_traceback)]
        obj.exception_type = str(type(e))
        obj.creator = creator
        obj.created = utcnow()
        obj.save()
        return obj


class XMLVersion(MinioFile):
    """
    Tem função de guardar a versão do XML
    Tem objetivo de identificar o Documento (Artigo)
    """

    xml_doc_pid = models.ForeignKey(
        "PidProviderXML", on_delete=models.SET_NULL, null=True, blank=True
    )
    finger_print = models.CharField(max_length=65, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["finger_print"]),
        ]

    def __str__(self):
        return self.finger_print

    @classmethod
    def create(cls, xml_doc_pid, uri, creator, basename, finger_print):
        obj = cls()
        obj.xml_doc_pid = xml_doc_pid
        obj.basename = basename
        obj.uri = uri
        obj.finger_print = finger_print
        obj.creator = creator
        obj.created = utcnow()
        obj.save()
        return obj


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


class PidProviderXML(CommonControlField):
    """
    Representação de atributos do Doc que o identifique unicamente
    """

    article = models.ForeignKey(
        Article, on_delete=models.SET_NULL, null=True, blank=True
    )
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

    synchronized = models.BooleanField(null=True, blank=True, default=False)
    sync_failure = models.ForeignKey(
        SyncFailure, null=True, blank=True, on_delete=models.SET_NULL
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
            models.Index(fields=["synchronized"]),
        ]

    def __str__(self):
        return self.pkg_name or self.v3 or "PidProviderXML sem ID"

    @property
    def data(self):
        return {
            "v3": self.v3,
            "v2": self.v2,
            "aop_pid": self.aop_pid,
            "xml_uri": self.xml_uri,
            "article": self.article,
            "created": self.created and self.created.isoformat(),
            "updated": self.updated and self.updated.isoformat(),
        }

    @classmethod
    def xml_feed(
        cls, from_ingress_date=None, issn=None, pub_year=None, include_has_article=False
    ):
        """
        Retorna a lista de XML para alimentar o modelo Article e relacionados
        """
        params = {}
        if not include_has_article:
            params["article__isnull"] = True
        if from_ingress_date:
            params["updated__gte"] = from_ingress_date
        qs = None
        if issn:
            qs = Q(journal__issn_electronic=issn) | Q(journal__issn_print=issn)
        if pub_year:
            if qs:
                qs = qs & Q(issn__pub_year=pub_year)
            else:
                qs = Q(issn__pub_year=pub_year)

        if qs and params:
            yield from cls.objects.filter(qs, **params).order_by("updated").iterator()
        elif qs:
            yield from cls.objects.filter(qs).order_by("updated").iterator()
        elif params:
            yield from cls.objects.filter(**params).order_by("updated").iterator()
        else:
            yield from cls.objects.order_by("updated").iterator()

    @classmethod
    def unsynchronized(cls):
        """
        Identifica no pid provider local os registros que não
        estão sincronizados com o pid provider remoto (central) e
        faz a sincronização, registrando o XML local no pid provider remoto
        """
        return cls.objects.filter(synchronized=False).iterator()

    @property
    def xml_with_pre(self):
        try:
            self._xml_with_pre = get_xml_with_pre_from_uri(self.xml_uri)
        except Exception as e:
            raise exceptions.PidProviderXMLWithPreError(
                _("Unable to get xml with pre (PidProviderXML) {}: {} {}").format(
                    self.xml_uri, type(e), e
                )
            )
        return self._xml_with_pre

    @property
    def is_aop(self):
        return self.issue is None

    @property
    def xml_uri(self):
        try:
            return self.current_version.uri
        except AttributeError:
            return None

    def add_version(self, uri, creator, basename, finger_print):
        if (
            not self.current_version
            or self.current_version.finger_print != finger_print
        ):
            self.current_version = XMLVersion.create(
                self, uri, creator, basename, finger_print
            )
            self.save()

    @classmethod
    def get_xml_uri(cls, v3):
        try:
            item = cls.objects.get(v3=v3)
        except cls.DoesNotExist:
            return None
        else:
            return item.xml_uri

    @classmethod
    def register(
        cls, xml_with_pre, filename, user, push_xml_content, synchronized=None
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
                "basename": self.basename,
            }

        """
        try:
            pkg_name, ext = os.path.splitext(os.path.basename(filename))
            logging.info(f"PidProviderXML.register {filename}")

            # adaptador do xml with pre
            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)

            # consulta se documento já está registrado
            registered = cls._query_document(xml_adapter)

            # analisa se aceita ou rejeita registro
            evaluate_registration(xml_adapter, registered)

            # verfica os PIDs encontrados no XML / atualiza-os se necessário
            xml_changed = cls._complete_pids(xml_adapter, registered)

            data = {}
            if registered:
                data["record_status"] = "retrieved"
                if not registered.is_equal_to(xml_adapter):
                    registered._update(
                        xml_adapter,
                        user,
                        push_xml_content,
                        filename,
                        pkg_name,
                        synchronized,
                    )
                    data["record_status"] = "updated"
            else:
                registered = cls._create(
                    xml_adapter,
                    user,
                    push_xml_content,
                    filename,
                    pkg_name,
                    synchronized,
                )
                data["record_status"] = "created"

            data.update(registered.data)
            data["xml_changed"] = xml_changed
            return data

        except (
            exceptions.ForbiddenPidProviderXMLRegistrationError,
            exceptions.NotEnoughParametersToGetDocumentRecordError,
            exceptions.QueryDocumentMultipleObjectsReturnedError,
            PutXMLContentError,
        ) as e:
            bad_request = PidProviderBadRequest.get_or_create(
                user,
                filename,
                e,
                xml_adapter,
            )
            return bad_request.data

    def push_xml_content(self, xml_adapter, user, push_xml_content, filename):
        finger_print = xml_adapter.finger_print
        response = push_xml_content(
            filename=filename,
            subdirs="",
            content=xml_adapter.tostring(),
            finger_print=finger_print,
        )
        if response:
            self.add_version(
                uri=response["uri"],
                creator=user,
                basename=filename,
                finger_print=finger_print,
            )

    @classmethod
    def evaluate_registration(cls, xml_adapter, registered):
        """
        XML é versão AOP, mas
        documento está registrado com versão VoR (fascículo),
        então, recusar o registro,
        pois está tentando registrar uma versão desatualizada
        """
        if xml_adapter.is_aop and registered and not registered.is_aop:
            raise exceptions.ForbiddenPidProviderXMLRegistrationError(
                _(
                    "The XML content is an ahead of print version "
                    "but the document {} is already published in an issue"
                ).format(registered)
            )
        return True

    def set_synchronized(self, value, user):
        self.synchronized = value
        self.updated_by = user
        self.updated = utcnow()
        self.save()

    def is_equal_to(self, xml_adapter):
        return bool(
            self.current_version
            and self.current_version.finger_print == xml_adapter.finger_print
        )

    @classmethod
    def get_registration_demand(cls, xml_with_pre):
        """
        Verifica se há necessidade de registrar local (upload) e/ou
        remotamente (core)

        Parameters
        ----------
        xml_with_pre : XMLWithPre

        Raises
        ------
        exceptions.QueryDocumentMultipleObjectsReturnedError
        """
        required_remote = True
        required_local = True

        xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)

        try:
            registered = cls._query_document(xml_adapter)
        except (
            exceptions.NotEnoughParametersToGetDocumentRecordError,
            exceptions.QueryDocumentMultipleObjectsReturnedError,
        ) as e:
            logging.exception(e)
            return {"error": str(e)}

        if registered and registered.is_equal_to(xml_adapter):
            # skip local registration
            required_local = False
            required_remote = not registered.synchronized

        return dict(
            registered=registered and registered.data or {},
            required_local=required_local,
            required_remote=required_remote,
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
            {"error": str(e)}
        """
        xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
        try:
            registered = cls._query_document(xml_adapter)
        except (
            exceptions.NotEnoughParametersToGetDocumentRecordError,
            exceptions.QueryDocumentMultipleObjectsReturnedError,
        ) as e:
            logging.exception(e)
            return {"error": str(e)}
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

    @classmethod
    def _create(
        cls, xml_adapter, user, push_xml_content, filename, pkg_name, synchronized=None
    ):
        try:
            doc = cls()
            doc.creator = user
            doc.created = utcnow()
            doc.save()
            return doc._update(
                xml_adapter, user, push_xml_content, filename, pkg_name, synchronized
            )
        except Exception as e:
            LOGGER.exception(e)
            raise exceptions.PidProviderXMLCreateError(
                _("PidProviderXML create error: {} {} {}").format(
                    type(e),
                    e,
                    xml_adapter,
                )
            )

    def _update(
        self, xml_adapter, user, push_xml_content, filename, pkg_name, synchronized=None
    ):
        self.push_xml_content(xml_adapter, user, push_xml_content, filename)
        try:
            self._add_data(xml_adapter, user, pkg_name)
            self.synchronized = synchronized
            self.updated_by = user
            self.updated = utcnow()
            self.save()
            return self
        except Exception as e:
            LOGGER.exception(e)
            raise exceptions.PidProviderXMLUpdateError(
                _("PidProviderXML Update data error: {} {} {}").format(
                    type(e),
                    e,
                    xml_adapter,
                )
            )

    def _add_data(self, xml_adapter, user, pkg_name):
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

        self.z_article_titles_texts = xml_adapter.article_titles_texts
        self.z_surnames = xml_adapter.surnames
        self.z_collab = xml_adapter.collab
        self.z_links = xml_adapter.links
        self.z_partial_body = xml_adapter.partial_body

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
        return f"{xml_adapter.v2_prefix}{mmdd}{nnnnn}"

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
        before = (xml_adapter.v2, xml_adapter.v3, xml_adapter.aop_pid)

        # adiciona os pids faltantes aos dados de entrada
        cls._add_pid_v3(xml_adapter, registered)
        cls._add_pid_v2(xml_adapter, registered)
        cls._add_aop_pid(xml_adapter, registered)

        after = (xml_adapter.v2, xml_adapter.v3, xml_adapter.aop_pid)

        LOGGER.info("%s %s" % (before, after))
        return before != after

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
