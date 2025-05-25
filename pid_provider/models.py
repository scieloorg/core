import os
import json
import logging
import sys
import traceback
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import models, IntegrityError
from django.db.models import Q
from django.utils.translation import gettext as _
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre
from packtools.sps.pid_provider import v3_gen, xml_sps_adapter
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import Orderable
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel
from django_prometheus.models import ExportModelOperationsMixin

from collection.models import Collection
from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from pid_provider import exceptions
from pid_provider import choices
from pid_provider.query_params import get_valid_query_parameters, get_xml_adapter_data
from tracker.models import UnexpectedEvent, BaseEvent

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class XMLVersionXmlWithPreError(Exception): ...


class XMLVersionLatestError(Exception): ...


class XMLVersionGetError(Exception): ...


class PidProviderXMLPidV3ConflictError(Exception): ...


class PidProviderXMLPidV2ConflictError(Exception): ...


class PidProviderXMLPidAOPConflictError(Exception): ...


def utcnow():
    return datetime.utcnow()
    # return datetime.utcnow().isoformat().replace("T", " ") + "Z"


def xml_directory_path(instance, filename):
    sps_pkg_name = instance.pid_provider_xml.pkg_name
    subdirs = sps_pkg_name.split("-")
    subdir_sps_pkg_name = "/".join(subdirs)
    return f"pid_provider/{subdir_sps_pkg_name}/{filename}"


class XMLVersion(CommonControlField):
    """
    Tem função de guardar a versão do XML
    """

    pid_provider_xml = models.ForeignKey(
        "PidProviderXML", null=True, blank=True, on_delete=models.SET_NULL
    )
    file = models.FileField(upload_to=xml_directory_path, null=True, blank=True)
    finger_print = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["finger_print"]),
            models.Index(fields=["pid_provider_xml"]),
        ]

    def __str__(self):
        return f"{self.pid_provider_xml.pkg_name} {self.created}"

    @classmethod
    def create(
        cls,
        user,
        pid_provider_xml,
        xml_with_pre,
    ):
        try:
            obj = cls()
            obj.pid_provider_xml = pid_provider_xml
            obj.finger_print = xml_with_pre.finger_print
            obj.creator = user
            obj.save()
            obj.save_file(
                f"{pid_provider_xml.v3}.xml", xml_with_pre.tostring(pretty_print=True)
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(pid_provider_xml, xml_with_pre.finger_print)

    def save_file(self, filename, content):
        try:
            self.file.delete(save=False)
        except Exception as e:
            logging.exception(e)
        self.file.save(filename, ContentFile(content))

    def is_equal_to(self, xml_with_pre):
        return os.path.isfile(self.file.path) and (
            self.finger_print == xml_with_pre.finger_print
        )

    @property
    def xml_with_pre(self):
        if not os.path.isfile(self.file.path):
            raise FileNotFoundError(
                _("Unable to read XML {} {}").format(self.file.path, self)
            )
        try:
            for item in XMLWithPre.create(path=self.file.path):
                return item
        except Exception as e:
            raise XMLVersionXmlWithPreError(
                _("Unable to get xml with pre (XMLVersion) {}: {} {}").format(
                    self.pid_provider_xml.v3, type(e), e
                )
            )

    @property
    def xml(self):
        try:
            return self.xml_with_pre.tostring(pretty_print=True)
        except XMLVersionXmlWithPreError as e:
            return str(e)
        except FileNotFoundError as e:
            return None

    @classmethod
    def latest(cls, pid_provider_xml):
        if pid_provider_xml:
            # Adicionar select_related para evitar query extra ao acessar pid_provider_xml
            item = (
                cls.objects.select_related("pid_provider_xml")
                .filter(pid_provider_xml=pid_provider_xml)
                .latest("created")
            )
            if item and os.path.isfile(item.file.path):
                return item
            raise cls.DoesNotExist(f"{pid_provider_xml}")
        raise XMLVersionLatestError(
            "XMLVersion.latest: unable to get {}".format(pid_provider_xml)
        )

    @classmethod
    def get(cls, pid_provider_xml, finger_print):
        """
        Retorna última versão se finger_print corresponde
        """
        if not pid_provider_xml and not finger_print:
            raise XMLVersionGetError(
                "XMLVersion.get requires pid_provider_xml and xml_with_pre parameters"
            )
        latest = cls.latest(pid_provider_xml)
        if latest.finger_print == finger_print:
            return latest
        raise cls.DoesNotExist(f"{pid_provider_xml} {finger_print}")

    @classmethod
    def get_or_create(cls, user, pid_provider_xml, xml_with_pre):
        try:
            latest = cls.select_related("pid_provider_xml").get(
                pid_provider_xml, xml_with_pre.finger_print
            )
            if not os.path.isfile(latest.file.path):
                latest.save_file(
                    f"{pid_provider_xml.v3}.xml",
                    xml_with_pre.tostring(pretty_print=True),
                )
                latest.save()
            return latest
        except cls.DoesNotExist:
            return cls.create(
                user=user,
                pid_provider_xml=pid_provider_xml,
                xml_with_pre=xml_with_pre,
            )


class PidProviderConfig(CommonControlField, ClusterableModel):
    """
    Tem função de guardar XML que falhou no registro
    """

    pid_provider_api_post_xml = models.CharField(
        _("XML Post URI"), max_length=2048, null=True, blank=True
    )
    pid_provider_api_get_token = models.CharField(
        _("Get Token URI"), max_length=2048, null=True, blank=True
    )
    timeout = models.IntegerField(_("Timeout"), null=True, blank=True)
    api_username = models.CharField(
        _("API Username"), max_length=150, null=True, blank=True
    )
    api_password = models.CharField(
        _("API Password"), max_length=255, null=True, blank=True
    )

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
        InlinePanel("endpoint", label=_("Endpoints")),
    ]

    base_form_class = CoreAdminModelForm


class PidProviderEndpoint(CommonControlField):
    """
    Registro de PIDs (associados a um PidProviderXML) cujo valor difere do valor atribuído
    """

    config = ParentalKey(
        "PidProviderConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="endpoint",
    )
    name = models.CharField(
        _("Endpoint name"),
        max_length=16,
        null=True,
        blank=True,
        choices=choices.ENDPOINTS,
    )
    url = models.URLField(_("Endpoint URL"), max_length=128, null=True, blank=True)
    enabled = models.BooleanField(default=False)

    panels = [
        FieldPanel("name"),
        FieldPanel("url"),
        FieldPanel("enabled"),
    ]

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["enabled"]),
        ]

    def __str__(self):
        return f"{self.url} {self.enabled}"


class PidRequest(CommonControlField):
    origin = models.CharField(
        _("Request origin"), max_length=124, null=True, blank=True
    )
    result_type = models.CharField(
        _("Result type"), max_length=100, null=True, blank=True
    )
    result_msg = models.TextField(_("Result message"), null=True, blank=True)
    detail = models.JSONField(_("Detail"), null=True, blank=True)
    origin_date = models.CharField(
        _("Origin date"), max_length=10, null=True, blank=True
    )
    times = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "result_type",
                ]
            ),
        ]

    @property
    def data(self):
        _data = {
            "origin": self.origin,
            "origin_date": self.origin_date,
            "result_type": self.result_type,
            "result_msg": self.result_msg,
            "detail": self.detail,
            "times": self.times,
        }
        return _data

    def __unicode__(self):
        return f"{self.origin}"

    def __str__(self):
        return f"{self.origin}"

    @classmethod
    def get(
        cls,
        origin,
    ):
        if origin:
            return cls.objects.get(origin=origin)
        raise ValueError("PidRequest.get requires parameters")

    @classmethod
    def create_or_update(
        cls,
        user=None,
        origin=None,
        result_type=None,
        result_msg=None,
        detail=None,
        origin_date=None,
    ):
        try:
            obj = cls.get(origin=origin)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user
            obj.origin = origin
        obj.result_type = result_type
        obj.result_msg = result_msg
        obj.detail = detail
        obj.origin_date = origin_date
        if not obj.times:
            obj.times = 0
        obj.times += 1
        obj.save()
        return obj

    @classmethod
    def register_failure(
        cls,
        e,
        user=None,
        origin=None,
        origin_date=None,
        detail=None,
    ):
        logging.exception(e)
        return PidRequest.create_or_update(
            user=user,
            origin=origin,
            origin_date=origin_date,
            result_type=str(type(e)),
            result_msg=str(e),
            detail=detail,
        )

    @classmethod
    def cancel_failure(
        cls, user=None, origin=None
    ):
        try:
            PidRequest.get(origin).delete()
        except cls.DoesNotExist:
            # nao é necessario atualizar o status de falha não registrada anteriormente
            pass

    @property
    def created_updated(self):
        return self.updated or self.created

    @classmethod
    def items_to_retry(cls):
        # Adicionar select_related se for acessar xml_version posteriormente
        return (
            cls.objects
            .filter(~Q(result_type="OK"), origin__contains=":")
            .iterator()
        )

    panels = [
        # FieldPanel("origin", read_only=True),
        FieldPanel("origin_date", read_only=True),
        FieldPanel("result_type", read_only=True),
        FieldPanel("result_msg", read_only=True),
        # AutocompletePanel("xml_version", read_only=True),
        FieldPanel("detail", read_only=True),
    ]

    base_form_class = CoreAdminModelForm


class OtherPid(CommonControlField):
    """
    Registro de PIDs (associados a um PidProviderXML) cujo valor difere do valor atribuído
    """

    pid_provider_xml = ParentalKey(
        "PidProviderXML",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="other_pid",
    )
    pid_type = models.CharField(_("PID type"), max_length=7, null=True, blank=True)
    pid_in_xml = models.CharField(
        _("PID pid_in_xml"), max_length=64, null=True, blank=True
    )
    version = models.ForeignKey(
        XMLVersion, null=True, blank=True, on_delete=models.SET_NULL
    )

    panels = [
        # FieldPanel("pid_provider_xml", read_only=True),
        FieldPanel("pid_type", read_only=True),
        FieldPanel("pid_in_xml", read_only=True),
        AutocompletePanel("version", read_only=True),
    ]

    class Meta:
        indexes = [
            models.Index(fields=["pid_in_xml"]),
            models.Index(fields=["pid_type"]),
            models.Index(fields=["version"]),
        ]

    def __str__(self):
        return f"{self.pid_type} {self.pid_in_xml} {self.created}"

    @classmethod
    def get_or_create(cls, pid_type, pid_in_xml, version, user, pid_provider_xml):
        if pid_in_xml and pid_type and version and user and pid_provider_xml:
            try:
                obj = cls.objects.get(
                    pid_provider_xml=pid_provider_xml,
                    pid_type=pid_type,
                    pid_in_xml=pid_in_xml,
                    version=version,
                )
            except cls.DoesNotExist:
                obj = cls()
                obj.creator = user
                obj.pid_provider_xml = pid_provider_xml
                obj.pid_type = pid_type
                obj.pid_in_xml = pid_in_xml
                obj.version = version
                obj.save()

            return obj
        raise ValueError(
            f"OtherPid.get_or_create requires pid_in_xml ({pid_in_xml}) and pid_type ({pid_type}) and version ({version}) and user ({user}) and pid_provider_xml ({pid_provider_xml})"
        )

    @property
    def created_updated(self):
        return self.updated or self.created


class PidProviderXML(
    ExportModelOperationsMixin("pidproviderxml"), CommonControlField, ClusterableModel
):
    """
    Tem responsabilidade de garantir a atribuição do PID da versão 3,
    armazenando dados chaves que garantem a identificação do XML
    """

    issn_electronic = models.CharField(
        _("issn_epub"), max_length=10, null=True, blank=True
    )
    issn_print = models.CharField(_("issn_ppub"), max_length=10, null=True, blank=True)
    pub_year = models.CharField(_("pub_year"), max_length=4, null=True, blank=True)
    volume = models.CharField(_("volume"), max_length=16, null=True, blank=True)
    number = models.CharField(_("number"), max_length=16, null=True, blank=True)
    suppl = models.CharField(_("suppl"), max_length=16, null=True, blank=True)

    current_version = models.ForeignKey(
        XMLVersion, on_delete=models.SET_NULL, null=True, blank=True
    )

    pkg_name = models.CharField(
        _("Package name"), max_length=100, null=True, blank=True
    )
    v3 = models.CharField(_("v3"), max_length=23, null=True, blank=True)
    v2 = models.CharField(_("v2"), max_length=24, null=True, blank=True)
    aop_pid = models.CharField(_("AOP PID"), max_length=64, null=True, blank=True)

    elocation_id = models.CharField(
        _("elocation id"), max_length=64, null=True, blank=True
    )
    fpage = models.CharField(_("fpage"), max_length=20, null=True, blank=True)
    fpage_seq = models.CharField(_("fpage_seq"), max_length=8, null=True, blank=True)
    lpage = models.CharField(_("lpage"), max_length=20, null=True, blank=True)
    article_pub_year = models.CharField(
        _("Document Publication Year"), max_length=4, null=True, blank=True
    )
    main_doi = models.CharField(_("DOI"), max_length=255, null=True, blank=True)

    z_surnames = models.CharField(_("surnames"), max_length=64, null=True, blank=True)
    z_collab = models.CharField(_("collab"), max_length=64, null=True, blank=True)
    z_links = models.CharField(_("links"), max_length=64, null=True, blank=True)
    z_partial_body = models.CharField(
        _("partial_body"), max_length=64, null=True, blank=True
    )
    # data de atualização / criação do registro fonte
    origin_date = models.CharField(
        _("Origin date"), max_length=10, null=True, blank=True
    )
    # data de primeira publicação no site
    # evita que artigos WIP fique disponíveis antes de estarem públicos
    available_since = models.CharField(
        _("Available since"), max_length=10, null=True, blank=True
    )
    other_pid_count = models.PositiveIntegerField(default=0)
    registered_in_core = models.BooleanField(default=False)

    base_form_class = CoreAdminModelForm

    panel_a = [
        FieldPanel("registered_in_core", read_only=True),
        FieldPanel("issn_electronic", read_only=True),
        FieldPanel("issn_print", read_only=True),
        FieldPanel("pub_year", read_only=True),
        FieldPanel("volume", read_only=True),
        FieldPanel("number", read_only=True),
        FieldPanel("suppl", read_only=True),
        # FieldPanel("pkg_name", read_only=True),
        # FieldPanel("v3", read_only=True),
        FieldPanel("v2", read_only=True),
        FieldPanel("aop_pid", read_only=True),
        FieldPanel("main_doi", read_only=True),
        FieldPanel("elocation_id", read_only=True),
        FieldPanel("fpage", read_only=True),
        FieldPanel("fpage_seq", read_only=True),
        FieldPanel("lpage", read_only=True),
        FieldPanel("available_since", read_only=True),
        # FieldPanel("z_surnames", read_only=True),
        # FieldPanel("z_collab", read_only=True),
        # FieldPanel("z_links", read_only=True),
        # FieldPanel("z_partial_body", read_only=True),
    ]
    panel_b = [
        AutocompletePanel("current_version", read_only=True),
        InlinePanel("other_pid", label=_("Other PID")),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panel_a, heading=_("Identification")),
            ObjectList(panel_b, heading=_("Other PIDs")),
        ]
    )

    class Meta:
        ordering = ["-updated", "-created", "pkg_name"]
        indexes = [
            # === Essenciais ===
            models.Index(fields=["pkg_name"]),
            models.Index(fields=["v3"]),
            models.Index(fields=["v2"]),
            models.Index(fields=["issn_electronic"]),
            models.Index(fields=["issn_print"]),
            models.Index(fields=["pub_year"]),
            models.Index(fields=["article_pub_year"]),
            models.Index(fields=["main_doi"]),
            models.Index(fields=["registered_in_core"]),
            # === Compostos ===
            models.Index(fields=["issn_electronic", "article_pub_year"]),
            models.Index(fields=["issn_print", "article_pub_year"]),
            models.Index(fields=["pub_year", "volume", "number", "suppl"]),
            models.Index(fields=["issn_electronic", "main_doi"]),
            models.Index(fields=["issn_print", "main_doi"]),
            models.Index(fields=["issn_electronic", "elocation_id"]),
            models.Index(fields=["z_surnames", "article_pub_year"]),
            models.Index(fields=["z_collab", "article_pub_year"]),
        ]

    def __str__(self):
        return f"{self.pkg_name} {self.v3}"

    @classmethod
    def public_items(cls, from_date):
        now = datetime.utcnow().isoformat()[:10]
        return cls.objects.filter(
            (Q(available_since__isnull=True) | Q(available_since__lte=now))
            & (Q(created__gte=from_date) | Q(updated__gte=from_date)),
            current_version__pid_provider_xml__v3__isnull=False,
        ).iterator()

    @property
    def created_updated(self):
        return self.updated or self.created

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
            "registered_in_core": self.registered_in_core,
        }
        return _data

    @classmethod
    def get_xml_with_pre(cls, v3):
        try:
            # Usar select_related para evitar query extra ao acessar current_version
            obj = cls.objects.select_related("current_version").get(v3=v3)
            return obj.xml_with_pre
        except cls.DoesNotExist:
            return None
        except Exception:
            return None

    @property
    def xml_with_pre(self):
        return self.current_version and self.current_version.xml_with_pre

    @property
    def is_aop(self):
        return self.volume is None and self.number is None and self.suppl is None

    @classmethod
    def _check_pids_availability(cls, user, xml_adapter, registered):
        """
        No XML tem que conter os pids pertencentes ao registrado ou
        caso não é registrado, tem que ter pids inéditos.
        Também pode acontecer de o XML registrado ter mais de um pid v3, v2, ...
        Pode haver necessidade de atualizar o valor de pid v3, v2, ...
        Mudança em pid não é recomendado, mas pode acontecer

        Parameters
        ----------
        xml_adapter: PidProviderXMLAdapter
        registered: PidProviderXML

        Returns
        -------
        list of dict: keys=(pid_type, pid_in_xml, registered)

        """
        changed_pids = []
        pids = []
        if registered:
            pids = registered.get_pids()

        if xml_adapter.v3 and xml_adapter.v3 not in pids:
            item = cls._check_pid_availability(
                xml_pid_value=xml_adapter.v3,
                pid_name="v3",
                pid_type="pid_v3",
                ConflictException=PidProviderXMLPidV3ConflictError,
                registered=registered,
                registered_pid=registered and registered.v3,
            )
            if item:
                changed_pids.append(item)

        if xml_adapter.v2 and xml_adapter.v2 not in pids:
            item = cls._check_pid_availability(
                xml_pid_value=xml_adapter.v2,
                pid_name="v2",
                pid_type="pid_v2",
                ConflictException=PidProviderXMLPidV2ConflictError,
                registered=registered,
                registered_pid=registered and registered.v2,
            )
            if item:
                changed_pids.append(item)

        if xml_adapter.aop_pid and xml_adapter.aop_pid not in pids:
            item = cls._check_pid_availability(
                xml_pid_value=xml_adapter.aop_pid,
                pid_name="aop_pid",
                pid_type="aop_pid",
                ConflictException=PidProviderXMLPidAOPConflictError,
                registered=registered,
                registered_pid=registered and registered.aop_pid,
            )
            if item:
                changed_pids.append(item)

        registered._add_other_pid(changed_pids, user)
        return changed_pids

    @classmethod
    def _check_pid_availability(
        cls,
        xml_pid_value,
        pid_name,
        pid_type,
        ConflictException,
        registered,
        registered_pid,
    ):
        # pid no xml é novo
        param = {pid_name: xml_pid_value}
        owner = cls._is_registered_pid(**param)
        if owner:
            # e está registrado para outro XML
            raise ConflictException(
                f"PID {xml_pid_value} belongs to {owner} ({owner.get_pids()})"
            )
        elif registered:
            # indica a diferença do pid registrado e do pid do XML
            return {
                "pid_type": pid_type,
                "pid_in_xml": xml_pid_value,
                "registered": registered_pid,
            }

    @classmethod
    def register(
        cls,
        xml_with_pre,
        filename,
        user,
        origin_date=None,
        force_update=None,
        is_published=False,
        available_since=None,
        origin=None,
        registered_in_core=None,
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
            timeline = None

            input_data = {}
            input_data["xml_with_pre.data"] = xml_with_pre.data
            input_data["filename"] = filename
            input_data["origin"] = origin

            logging.info(f"PidProviderXML.register: {input_data}")

            timeline = PidProviderXMLTimeline.create_or_update(
                user,
                procedure="registration",
                pkg_name=xml_with_pre.sps_pkg_name,
                v3=xml_with_pre.v3,
                v2=xml_with_pre.v2,
                aop_pid=xml_with_pre.aop_pid,
                detail=input_data,
            )

            if not xml_with_pre.v3:
                raise exceptions.InvalidPidError(
                    f"Unable to register {filename}, because v3 was not present in the XML"
                )

            if not xml_with_pre.v2:
                raise exceptions.InvalidPidError(
                    f"Unable to register {filename}, because v2 was not present in the XML"
                )

            # adaptador do xml with pre
            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
            data = get_xml_adapter_data(xml_adapter)

            # consulta se documento já está registrado
            try:
                registered = cls._get_record(xml_adapter)
            except cls.DoesNotExist as exc:
                registered = None
            except cls.MultipleObjectsReturned as exc:
                raise exceptions.QueryDocumentMultipleObjectsReturnedError(exc)
            except (
                exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError
            ) as exc:
                raise exc
            except exceptions.RequiredISSNErrorToGetPidProviderXMLError as exc:
                raise exc
            except exceptions.NotEnoughParametersToGetPidProviderXMLError as exc:
                raise exc

            # analisa se está atualizado
            updated_data = cls.is_updated(
                xml_with_pre,
                registered,
                force_update,
                origin_date,
                registered_in_core,
            )
            if updated_data:
                timeline.add_event(
                    name="finish", detail="already up-to-date"
                )
                return updated_data

            # valida os PIDs do XML
            # - não podem ter conflito com outros registros
            # - identifica mudança
            changed_pids = cls._check_pids_availability(user, xml_adapter, registered)
            # cria ou atualiza registro
            registered = cls._save(
                registered,
                xml_adapter,
                user,
                origin_date,
                available_since,
                registered_in_core,
            )

            # data to return
            data = registered.data.copy()
            data["changed_pids"] = changed_pids
            timeline.add_event(
                name="finish",
                detail=data,
            )
            response = input_data
            response.update(data)
            return response

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if not timeline:
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail=input_data,
                )
                raise

            event = timeline.add_event(
                name="finish",
                exception=e,
                exc_type=exc_type,
                exc_value=exc_value,
                exc_traceback=exc_traceback,
            )
            response = input_data
            response.update(event.data)
            return response

    @classmethod
    def _save(
        cls,
        registered,
        xml_adapter,
        user,
        origin_date=None,
        available_since=None,
        registered_in_core=None,
    ):
        if registered:
            registered.updated_by = user
            registered.updated = utcnow()
        else:
            registered = cls()
            registered.creator = user
            registered.created = utcnow()

        # evita que artigos WIP fique disponíveis antes de estarem públicos
        try:
            registered.available_since = available_since or (
                xml_adapter.xml_with_pre.article_publication_date
            )
        except Exception as e:
            # packtools error
            registered.available_since = origin_date

        registered.registered_in_core = registered_in_core
        registered.origin_date = origin_date
        registered._add_data(xml_adapter, user)
        registered._add_journal(xml_adapter)
        registered._add_issue(xml_adapter)

        registered.save()

        registered._add_current_version(xml_adapter.xml_with_pre, user)

        return registered

    @classmethod
    def is_updated(
        cls, xml_with_pre, registered, force_update, origin_date, registered_in_core
    ):
        """
        XML é versão AOP, mas
        documento está registrado com versão VoR (fascículo),
        então, recusar o registro,
        pois está tentando registrar uma versão desatualizada
        """
        if force_update:
            logging.info(f"Do not skip update: force_update")
            return

        if not registered:
            logging.info(f"Do not skip update: not registered")
            return

        if registered_in_core != registered.registered_in_core:
            logging.info(f"Do not skip update: need to update registered_in_core")
            return

        # verifica se é necessário atualizar
        if registered.is_equal_to(xml_with_pre):
            # XML fornecido é igual ao registrado, não precisa continuar
            logging.info(f"Skip update: equal")
            return registered.data

        if xml_with_pre.is_aop and registered and not registered.is_aop:
            logging.info(f"Skip update: forbidden")
            raise exceptions.ForbiddenPidProviderXMLRegistrationError(
                _(
                    "The XML content is an ahead of print version "
                    "but the document {} is already published in an issue"
                ).format(registered)
            )

        if (
            origin_date
            and registered.origin_date
            and registered.origin_date > origin_date
        ):
            # retorna item registrado que está mais atualizado
            logging.info(f"Skip update: is already up-to-date")
            return registered.data

    def is_equal_to(self, xml_with_pre):
        return bool(
            self.current_version and self.current_version.is_equal_to(xml_with_pre)
        )

    @classmethod
    def _get_record(cls, xml_adapter):
        """
        Get record

        Arguments
        ---------
        xml_adapter : PidProviderXMLAdapter

        Returns
        -------
        PidProviderXML

        Raises
        ------
        DoesNotExist
        MultipleObjectsReturned
        RequiredPublicationYearErrorToGetPidProviderXMLError
            Se o ano de publicação requerido não estiver disponível.
        RequiredISSNErrorToGetPidProviderXMLError
            Se nem o ISSN eletrônico nem o impresso estiverem disponíveis.
        NotEnoughParametersToGetPidProviderXMLError
            Se os parâmetros disponíveis forem insuficientes para desambiguação.

        """
        q, query_list = get_valid_query_parameters(xml_adapter)

        # Usar select_related para otimizar acesso futuro a current_version
        queryset = cls.objects.select_related("current_version")

        try:
            # versão VoR (version of record)
            return queryset.get(q, **query_list[0])
        except cls.DoesNotExist:
            try:
                # versão aop (ahead of print)
                return queryset.get(q, **query_list[1])
            except IndexError:
                raise cls.DoesNotExist

    @classmethod
    def _get_records(cls, xml_adapter):
        """
        Get record

        Arguments
        ---------
        xml_adapter : PidProviderXMLAdapter

        Returns
        -------
        PidProviderXML generator

        Raises
        ------
        RequiredPublicationYearErrorToGetPidProviderXMLError
            Se o ano de publicação requerido não estiver disponível.
        RequiredISSNErrorToGetPidProviderXMLError
            Se nem o ISSN eletrônico nem o impresso estiverem disponíveis.
        NotEnoughParametersToGetPidProviderXMLError
            Se os parâmetros disponíveis forem insuficientes para desambiguação.

        """
        q, query_list = get_valid_query_parameters(xml_adapter)
        yield from cls.objects.select_related("current_version").filter(
            q, **query_list[0]
        )
        if len(query_list) > 1:
            yield from cls.objects.select_related("current_version").filter(
                q, **query_list[1]
            )

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
        items = xml_adapter.query_list
        for params in items:
            cls.validate_query_params(params)

            adapted_params_ = xml_adapter.adapt_query_params(params)

            if adapted_params_.get("issue__isnull"):
                adapted_params_.pop("issue__isnull")
                adapted_params_["volume__isnull"] = True
                adapted_params_["number__isnull"] = True
                adapted_params_["suppl__isnull"] = True
            adapted_params = {
                name.replace("journal__", "").replace("issue__", ""): v
                for name, v in adapted_params_.items()
            }

            try:
                return cls.objects.get(**adapted_params)
            except cls.DoesNotExist:
                continue
            except cls.MultipleObjectsReturned as e:
                # seria inesperado já que os dados informados devem encontrar
                # ocorrência única ou None
                items = []
                for item in cls.objects.filter(**adapted_params).iterator():
                    items.append(item.data)
                # try:
                #     cls.objects.filter(**adapted_params).delete()
                #     deleted = True
                # except Exception as e:
                #     logging.exception(e)
                #     deleted = str(e)

                raise exceptions.QueryDocumentMultipleObjectsReturnedError(
                    str({"params": adapted_params, "items": items})
                )

    def _add_data(self, xml_adapter, user):
        self.pkg_name = xml_adapter.sps_pkg_name
        self.article_pub_year = xml_adapter.article_pub_year
        self.v3 = xml_adapter.v3
        self.v2 = xml_adapter.v2
        self.aop_pid = xml_adapter.aop_pid

        self.fpage = xml_adapter.fpage
        self.fpage_seq = xml_adapter.fpage_seq
        self.lpage = xml_adapter.lpage

        self.main_doi = xml_adapter.main_doi
        self.elocation_id = xml_adapter.elocation_id

        self.z_surnames = xml_adapter.z_surnames
        self.z_collab = xml_adapter.z_collab
        self.z_links = xml_adapter.z_links
        self.z_partial_body = xml_adapter.z_partial_body

    def _add_journal(self, xml_adapter):
        self.issn_electronic = xml_adapter.journal_issn_electronic
        self.issn_print = xml_adapter.journal_issn_print

    def _add_issue(self, xml_adapter):
        self.volume = xml_adapter.volume
        self.number = xml_adapter.number
        self.suppl = xml_adapter.suppl
        self.pub_year = xml_adapter.pub_year

    def _add_current_version(self, xml_with_pre, user, delete=Fase):
        if delete:
            try:
                self.current_version.delete()
            except Exception as e:
                pass

        self.current_version = XMLVersion.get_or_create(user, self, xml_with_pre)
        self.save()

    def _add_other_pid(self, changed_pids, user):
        # registrados passam a ser other pid
        # os pids do XML passam a ser os vigentes
        if not changed_pids:
            return
        self.save()
        for change_args in changed_pids:

            change_args["pid_in_xml"] = change_args.pop("registered")

            change_args["user"] = user
            change_args["version"] = self.current_version
            change_args["pid_provider_xml"] = self

            OtherPid.get_or_create(**change_args)
        self.other_pid_count = OtherPid.objects.filter(pid_provider_xml=self).count()
        self.save()

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
            items = cls.objects.filter(v3=v3)
        elif v2:
            items = cls.objects.filter(v2=v2)
        elif aop_pid:
            items = cls.objects.filter(Q(v2=aop_pid) | Q(aop_pid=aop_pid))
        else:
            return None
        try:
            return items[0]
        except IndexError:
            try:
                obj = OtherPid.objects.get(pid_in_xml=v3 or v2 or aop_pid)
                return obj.pid_provider_xml
            except OtherPid.DoesNotExist:
                return None

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
    def complete_pids(
        cls,
        xml_with_pre,
    ):
        """
        Evaluate the XML data and complete xml_with_pre with PID v3, v2, aop_pid

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
        """
        try:
            # adaptador do xml with pre
            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
            data = get_xml_adapter_data(xml_adapter)

            # consulta se documento já está registrado
            try:
                registered = cls._get_record(xml_adapter)
            except cls.DoesNotExist as exc:
                registered = None
            except cls.MultipleObjectsReturned as exc:
                raise exceptions.QueryDocumentMultipleObjectsReturnedError(exc)
            except (
                exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError
            ) as exc:
                raise exc
            except exceptions.RequiredISSNErrorToGetPidProviderXMLError as exc:
                raise exc
            except exceptions.NotEnoughParametersToGetPidProviderXMLError as exc:
                raise exc

            # verfica os PIDs encontrados no XML / atualiza-os se necessário
            changed_pids = cls._complete_pids(xml_adapter, registered)

            logging.info(
                f"PidProviderXML.complete_pids: input={xml_with_pre.data} | output={changed_pids}"
            )
            return changed_pids

        except Exception as e:
            # except (
            #     exceptions.NotEnoughParametersToGetDocumentRecordError,
            #     exceptions.QueryDocumentMultipleObjectsReturnedError,
            # ) as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "PidProviderXML.complete_pids",
                    "detail": xml_with_pre.data,
                },
            )
            return {"error_message": str(e), "error_type": str(type(e))}

    @classmethod
    def _complete_pids(cls, xml_adapter, registered):
        """
        No XML pode conter ou não os PIDS v2, v3 e aop_pid.
        Na base de dados o documento do XML pode ou não estar registrado.

        O resultado deste procedimento é que seja garantido que os
        valores dos PIDs no XML sejam inéditos ou recuperados da base de dados.

        Se no XML existir os PIDs, os valores são verificados na base de dados,
        se são inéditos, não haverá mudança no XML, mas se os PIDs do XML
        conflitarem com os PIDs registrados ou seus valores forem inválidos,
        haverá mudança nos PIDs.

        Parameters
        ----------
        xml_adapter: PidProviderXMLAdapter
        registered: PidProviderXML

        Returns
        -------
        list of dict: keys=(pid_type, pid_in_xml, pid_assigned)

        """
        before = (xml_adapter.v3, xml_adapter.v2, xml_adapter.aop_pid)

        # garante que não há espaços extras
        if xml_adapter.v3:
            xml_adapter.v3 = xml_adapter.v3.strip()
        if xml_adapter.v2:
            xml_adapter.v2 = xml_adapter.v2.strip()
        if xml_adapter.aop_pid:
            xml_adapter.aop_pid = xml_adapter.aop_pid.strip()

        # adiciona os pids faltantes ao XML fornecido
        cls._add_pid_v3(xml_adapter, registered)
        cls._add_pid_v2(xml_adapter, registered)
        cls._add_aop_pid(xml_adapter, registered)

        after = (xml_adapter.v3, xml_adapter.v2, xml_adapter.aop_pid)

        # verifica se houve mudança nos PIDs do XML
        changes = {}
        for label, bef, aft in zip(("pid_v3", "pid_v2", "aop_pid"), before, after):
            if bef != aft:
                changes[label] = aft
        return changes

    @classmethod
    def _is_valid_pid(cls, value):
        return bool(value and len(value) == 23)

    def get_pids(self):
        pids = [self.v3]
        if self.v2:
            pids.append(self.v2)
        if self.aop_pid:
            pids.append(self.aop_pid)
        for item in OtherPid.objects.filter(pid_provider_xml=self).iterator():
            pids.append(item.pid_in_xml)
        return pids

    @classmethod
    def _add_pid_v3(cls, xml_adapter, registered):
        """
        Atribui v3 ao xml_adapter,
        recuperando do registered ou obtendo um v3 inédito

        Arguments
        ---------
        xml_adapter: PidProviderXMLAdapter
        registered: PidProviderXML
        """
        if (
            not xml_adapter.v3
            or not cls._is_valid_pid(xml_adapter.v3)
            or cls._is_registered_pid(v3=xml_adapter.v3)
        ):
            if registered:
                xml_adapter.v3 = registered.v3
            else:
                # obtém um v3 inédito
                xml_adapter.v3 = cls._get_unique_v3()

    @classmethod
    def _add_aop_pid(cls, xml_adapter, registered):
        """
        Atribui aop_pid ao xml_adapter, recuperando do registered, se existir

        Arguments
        ---------
        xml_adapter: PidProviderXMLAdapter
        registered: PidProviderXML
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
        registered: PidProviderXML

        """
        if (
            not xml_adapter.v2
            or not cls._is_valid_pid(xml_adapter.v2)
            or cls._is_registered_pid(v2=xml_adapter.v2)
        ):
            if registered:
                xml_adapter.v2 = registered.v2
            else:
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

    @classmethod
    def is_registered(cls, xml_with_pre, complete_missing_xml_pids_with_registered_pids=True):
        """
        Verifica se há necessidade de registrar, se está registrado e é igual

        Parameters
        ----------
        xml_with_pre : XMLWithPre

        """
        try:
            timeline = None
            input_data = {"xml_with_pre.data": xml_with_pre.data}
            timeline = PidProviderXMLTimeline.create_or_update(
                user,
                procedure="is_registered",
                pkg_name=xml_with_pre.sps_pkg_name,
                v3=xml_with_pre.v3,
                v2=xml_with_pre.v2,
                aop_pid=xml_with_pre.aop_pid,
                detail=input_data,
            )
            xml_adapter_data = None
            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
            xml_adapter_data = get_xml_adapter_data(xml_adapter)

            input_data["xml_adapter_data"] = xml_adapter_data
            timeline.detail = input_data
            timeline.save()

            try:
                registered = cls._get_record(xml_adapter)
            except cls.DoesNotExist as exc:
                timeline.add_event(
                    name="finish", detail="not registered"
                )
                return {"filename": xml_with_pre.filename, "registered": False}
            except cls.MultipleObjectsReturned as exc:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                response = {"error_msg": str(e), "error_type": str(type(e))}
                response["input_data"] = xml_adapter_data
                response["records"] = list(
                    record.data for record in cls._get_records(xml_adapter)
                )
                timeline.add_event(
                    name="finish",
                    detail=response,
                    exception=e,
                    exc_type=exc_type,
                    exc_value=exc_value,
                    exc_traceback=exc_traceback,
                )
                return response
            except (
                exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError
            ) as exc:
                raise exc
            except exceptions.RequiredISSNErrorToGetPidProviderXMLError as exc:
                raise exc
            except exceptions.NotEnoughParametersToGetPidProviderXMLError as exc:
                raise exc
            response = registered.data
            response["input_data"] = xml_adapter_data
            response["registered"] = True
            response["finger_print"] = registered.current_version.finger_print
            if complete_missing_xml_pids_with_registered_pids:
                response.update(registered.complete_missing_xml_pids_with_registered_pids(xml_with_pre))

            timeline.add_event(name="finish", detail=response)
            return response
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if timeline:
                timeline.add_event(
                    name="finish",
                    exception=e,
                    exc_type=exc_type,
                    exc_value=exc_value,
                    exc_traceback=exc_traceback,
                )
            else:
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail=input_data,
                )
            return {"error_msg": str(e), "error_type": str(type(e)), "input_data": input_data}
        return {}

    def complete_missing_xml_pids_with_registered_pids(self, xml_with_pre):
        # Completa os valores ausentes de pid com recuperados ou com inéditos
        xml_changed = {}
        try:
            original_pids = (xml_with_pre.v3, xml_with_pre.v2, xml_with_pre.aop_pid)
            xml_with_pre.v3 = xml_with_pre.v3 or registered_data["v3"]
            xml_with_pre.v2 = xml_with_pre.v2 or registered_data["v2"]
            xml_with_pre.aop_pid = xml_with_pre.aop_pid or registered_data["aop_pid"]

            # verifica se houve mudança nos PIDs do XML
            resulting_pids = (xml_with_pre.v3, xml_with_pre.v2, xml_with_pre.aop_pid)
            for label, original_pid, resulting_pid in zip(
                ("pid_v3", "pid_v2", "aop_pid"), original_pids, resulting_pids
            ):
                if original_pid != resulting_pid:
                    xml_changed[label] = resulting_pid
        except KeyError:
            pass
        return {
            "is_equal": self.is_equal_to(xml_with_pre),
            "xml_changed": xml_changed
        }

    @classmethod
    def fix_pid_v2(cls, user, pid_v3, correct_pid_v2):
        try:
            item = cls.objects.select_related("current_version").get(v3=pid_v3)
        except cls.DoesNotExist as e:
            raise cls.DoesNotExist(f"{e}: {pid_v3}")

        try:
            if correct_pid_v2 == item.v2:
                return item.data
            xml_with_pre = item.current_version.xml_with_pre
            xml_with_pre.v2 = correct_pid_v2
            item._add_current_version(xml_with_pre, user, delete=True)
            item.v2 = correct_pid_v2
            item.save()
            return item.data
        except Exception as e:
            raise exceptions.PidProviderXMLFixPidV2Error(
                f"Unable to fix pid v2 for {item.v3} {e} {type(e)}"
            )


class CollectionPidRequest(CommonControlField):
    """
    Uso exclusivo no Core
    para controlar a entrada de XML provenientes do AM
    registrando cada coleção e a data da coleta
    """

    collection = models.ForeignKey(
        Collection, on_delete=models.SET_NULL, null=True, blank=True
    )
    end_date = models.CharField(max_length=10, null=True, blank=True)

    panels = [
        FieldPanel("end_date"),
    ]

    base_form_class = CoreAdminModelForm

    class Meta:
        unique_together = [("collection",)]

    def __unicode__(self):
        return f"{self.collection}"

    def __str__(self):
        return f"{self.collection}"

    @classmethod
    def get(
        cls,
        collection=None,
    ):
        if collection:
            try:
                return cls.objects.get(collection=collection)
            except cls.MultipleObjectsReturned:
                obj = cls.objects.filter(collection=collection).first()
                for item in cls.objects.filter(collection=collection).iterator():
                    if item is obj:
                        continue
                    item.delete()
                return obj
        raise ValueError("PidRequest.get requires parameters")

    @classmethod
    def create(
        cls,
        user=None,
        collection=None,
        end_date=None,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.collection = collection
            obj.end_date = end_date
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(collection)

    @classmethod
    def create_or_update(
        cls,
        user=None,
        collection=None,
        end_date=None,
    ):
        try:
            obj = cls.get(collection=collection)
            obj.updated_by = user
            obj.end_date = end_date or obj.end_date or "1900-01-01"
            obj.save()
            return obj
        except cls.DoesNotExist:
            return cls.create(user, collection, end_date)


class FixPidV2(CommonControlField):
    """
    Uso exclusivo da aplicação Upload
    Para gerenciar os pids v2 que foram ou não corrigidos no Upload e no Core
    """

    pid_provider_xml = models.ForeignKey(
        PidProviderXML, on_delete=models.SET_NULL, null=True, blank=True, unique=True
    )
    incorrect_pid_v2 = models.CharField(
        _("Incorrect v2"), max_length=24, null=True, blank=True
    )
    correct_pid_v2 = models.CharField(
        _("Correct v2"), max_length=24, null=True, blank=True
    )
    fixed_in_upload = models.BooleanField(null=True, blank=True, default=None)
    fixed_in_core = models.BooleanField(null=True, blank=True, default=None)

    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("incorrect_pid_v2", read_only=True),
        FieldPanel("correct_pid_v2", read_only=True),
        FieldPanel("fixed_in_core"),
        FieldPanel("fixed_in_upload"),
    ]

    class Meta:
        ordering = ["-updated", "-created"]

        indexes = [
            models.Index(fields=["incorrect_pid_v2"]),
            models.Index(fields=["correct_pid_v2"]),
            models.Index(fields=["fixed_in_core"]),
            models.Index(fields=["fixed_in_upload"]),
        ]

    def __str__(self):
        return f"{self.pid_provider_xml.v3}"

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return FixPidV2.objects.filter(pid_provider_xml__v3__icontains=search_term)

    def autocomplete_label(self):
        return f"{self.pid_provider_xml.v3}"

    @classmethod
    def get(cls, pid_provider_xml=None):
        if pid_provider_xml:
            return cls.objects.get(pid_provider_xml=pid_provider_xml)
        raise ValueError("FixPidV2.get requires pid_v3")

    @classmethod
    def create(
        cls,
        user,
        pid_provider_xml=None,
        incorrect_pid_v2=None,
        correct_pid_v2=None,
        fixed_in_core=None,
        fixed_in_upload=None,
    ):
        if (
            correct_pid_v2 == incorrect_pid_v2
            or not correct_pid_v2
            or not incorrect_pid_v2
        ):
            raise ValueError(
                f"FixPidV2.create: Unable to register correct_pid_v2={correct_pid_v2} and incorrect_pid_v2={incorrect_pid_v2} to be fixed"
            )
        try:
            obj = cls()
            obj.pid_provider_xml = pid_provider_xml
            obj.incorrect_pid_v2 = incorrect_pid_v2
            obj.correct_pid_v2 = correct_pid_v2
            obj.fixed_in_core = fixed_in_core
            obj.fixed_in_upload = fixed_in_upload
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(pid_provider_xml)

    @classmethod
    def create_or_update(
        cls,
        user,
        pid_provider_xml=None,
        incorrect_pid_v2=None,
        correct_pid_v2=None,
        fixed_in_core=None,
        fixed_in_upload=None,
    ):
        try:
            obj = cls.get(
                pid_provider_xml=pid_provider_xml,
            )
            obj.updated_by = user
            obj.fixed_in_core = fixed_in_core or obj.fixed_in_core
            obj.fixed_in_upload = fixed_in_upload or obj.fixed_in_upload
            obj.save()
            return obj
        except cls.DoesNotExist:
            return cls.create(
                user,
                pid_provider_xml,
                incorrect_pid_v2,
                correct_pid_v2,
                fixed_in_core,
                fixed_in_upload,
            )

    @classmethod
    def get_or_create(
        cls,
        user,
        pid_provider_xml,
        correct_pid_v2,
    ):
        try:
            return cls.objects.get(
                pid_provider_xml=pid_provider_xml,
            )
        except cls.DoesNotExist:
            return cls.create(
                user,
                pid_provider_xml,
                pid_provider_xml.v2,
                correct_pid_v2,
                fixed_in_core=None,
                fixed_in_upload=None,
            )


class PidProviderXMLTimeline(CommonControlField, ClusterableModel):
    procedure = models.CharField(
        _("Procedure"), max_length=30, null=True, blank=True
    )
    pkg_name = models.CharField(
        _("Package name"), max_length=100, null=True, blank=True
    )
    v3 = models.CharField(_("v3"), max_length=23, null=True, blank=True)
    v2 = models.CharField(_("v2"), max_length=24, null=True, blank=True)
    aop_pid = models.CharField(_("aop_pid"), max_length=24, null=True, blank=True)
    detail = models.JSONField(null=True, blank=True)

    base_form_class = CoreAdminModelForm

    panel_id = [
        FieldPanel("v3"),
        FieldPanel("v2"),
        FieldPanel("aop_pid"),
        FieldPanel("detail"),
    ]
    panel_event = [
        InlinePanel("event"),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(panel_id, heading=_("Detail")),
            ObjectList(panel_event, heading=_("Events")),
        ]
    )

    class Meta:
        ordering = ["-updated", "-created", "pkg_name"]
        unique_together = [("pkg_name", "procedure")]
        indexes = [
            models.Index(fields=["pkg_name", "procedure"]),
            models.Index(fields=["v2", ]),
            models.Index(fields=["v3", ]),
            models.Index(fields=["aop_pid", ]),
        ]

    def __str__(self):
        return f"{self.pkg_name} {self.procedure}"

    @property
    def data(self):
        return {
            "procedure": self.procedure,
            "pkg_name": self.pkg_name,
            "v3": self.v3,
            "v2": self.v2,
            "aop_pid": self.aop_pid,
            "detail": self.detail
        }

    @classmethod
    def create(
        cls,
        user,
        procedure,
        pkg_name,
        v3=None,
        v2=None,
        aop_pid=None,
        detail=None,
    ):
        if not pkg_name and not procedure:
            raise ValueError(
                f"PidProviderXMLTimeline.create requires pkg_name and procedure"
            )
        try:
            obj = cls()
            obj.procedure = procedure
            obj.pkg_name = pkg_name
            obj.v3 = v3
            obj.v2 = v2
            obj.aop_pid = aop_pid
            obj.detail = detail
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(procedure, pkg_name)

    @classmethod
    def create_or_update(
        cls,
        user,
        procedure,
        pkg_name,
        v3=None,
        v2=None,
        aop_pid=None,
        detail=None
    ):
        if not pkg_name and not procedure:
            raise ValueError(
                f"PidProviderXMLTimeline.create_or_update requires pkg_name and procedure"
            )
        try:
            obj = cls.get(procedure, pkg_name)
            obj.updated_by = user
            obj.v3 = v3
            obj.v2 = v2
            obj.aop_pid = aop_pid
            obj.detail = detail
            obj.save()
            return obj
        except cls.DoesNotExist:
            return cls.create(user, procedure, pkg_name, v3, v2, aop_pid, detail)

    @classmethod
    def get(cls, procedure, pkg_name):
        return cls.objects.get(pkg_name=pkg_name, procedure=procedure)

    def add_event(
        self,
        name,
        detail=None,
        exception=None,
        exc_type=None,
        exc_value=None,
        exc_traceback=None,
    ):
        error = None
        if exception:
            error = dict(
                error_msg=str(exception),
                error_type=str(exc_type),
                exc_value=str(exc_value),
                exc_traceback=str(exc_traceback),
            )
        event = PidProviderXMLEvent(ppx_timeline=self, name=name, detail=detail, error=error)
        self.event.add(event)
        return event


class PidProviderXMLEvent(BaseEvent):
    ppx_timeline = ParentalKey(
        "PidProviderXMLTimeline",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="event",
    )

    error = models.JSONField(null=True, blank=True)

    panels = [
        FieldPanel("name", read_only=True),
        FieldPanel("detail", read_only=True),
        FieldPanel("error", read_only=True),
        FieldPanel("created", read_only=True),
    ]

    class Meta:
        # isso faz com que em InlinePanel mostre do mais recente para o mais antigo
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["ppx_timeline"]),
        ]

    @property
    def data(self):
        _data = {}
        _data.update({"name": self.name, "detail": self.detail})
        _data.update(self.error)
        return _data
