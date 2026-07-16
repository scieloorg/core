import io
import logging
import os
import sys
import traceback
import zipfile
from datetime import datetime
from functools import cached_property
from zlib import crc32

from django.core.files.base import ContentFile
from django.core.exceptions import FieldError
from django.db import IntegrityError, models
from django.db.models import Prefetch, Q, Count
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from packtools.sps.pid_provider import v3_gen, xml_sps_adapter
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtailautocomplete.edit_handlers import AutocompletePanel

from collection.models import Collection
from core.widgets import ReadOnlyPrettyJSONWidget
from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from core.utils.profiling_tools import (  # ajuste o import conforme sua estrutura
    profile_classmethod,
    profile_method,
    profile_property,
    profile_staticmethod,
)
from pid_provider import choices, exceptions
from pid_provider.query_params import (
    zero_to_none,
    compare,
    QueryBuilderPidProviderXML,
)
from tracker.models import BaseEvent, UnexpectedEvent

PARTIAL_BODY_MAX = 300

try:
    from django_prometheus.models import ExportModelOperationsMixin

    COLLECTION_PREFIX = "scielojournal"
except ImportError:
    COLLECTION_PREFIX = "journalproc"

    class BasePidProviderXML:
        """Base class for exportable models."""

        class Meta:
            abstract = True

else:

    class BasePidProviderXML(
        ExportModelOperationsMixin("pidproviderxml"),
    ):
        """Base class for exportable models."""

        class Meta:
            abstract = True


LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class XMLVersionXmlWithPreError(Exception): ...


class XMLVersionLatestError(Exception): ...


class XMLVersionGetError(Exception): ...


class PidProviderXMLPidV3ConflictError(Exception): ...


class PidProviderXMLPidV2ConflictError(Exception): ...


class PidProviderXMLPidAOPConflictError(Exception): ...


def string_to_5_digits(input_string):
    return (crc32(input_string.encode()) & 0xFFFFFFFF) % 100000


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
    file = models.FileField(upload_to=xml_directory_path, null=True, blank=True, max_length=300)
    finger_print = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["pid_provider_xml"]),
            models.Index(fields=["finger_print"]),
        ]

    def __str__(self):
        return f"{self.pid_provider_xml.pkg_name} {self.created}"

    @classmethod
    @profile_classmethod
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
        try:
            for item in XMLWithPre.create(path=self.file.path):
                return item
        except Exception as e:
            raise XMLVersionXmlWithPreError(
                _("Unable to get xml with pre (XMLVersion) {}: {} {}").format(
                    self.pid_provider_xml.v3, type(e), e
                )
            )

    @cached_property
    def xml(self):
        try:
            return self.xml_with_pre.tostring(pretty_print=True)
        except XMLVersionXmlWithPreError as e:
            return str(e)
        except FileNotFoundError as e:
            return None

    @classmethod
    @profile_classmethod
    def get(cls, pid_provider_xml, finger_print):
        """
        Retorna última versão se finger_print corresponde
        """
        if not pid_provider_xml or not finger_print:
            raise XMLVersionGetError(
                "XMLVersion.get requires pid_provider_xml and xml_with_pre parameters"
            )
        found = cls.objects.filter(
            pid_provider_xml=pid_provider_xml, finger_print=finger_print
        ).latest("created")
        if found:
            return found
        raise cls.DoesNotExist(f"{pid_provider_xml} {finger_print}")

    @classmethod
    @profile_classmethod
    def get_or_create(cls, user, pid_provider_xml, xml_with_pre):
        try:
            latest = cls.get(pid_provider_xml, xml_with_pre.finger_print)
            try:
                file_exist = os.path.isfile(latest.file.path)
            except (AttributeError, TypeError, ValueError) as e:
                file_exist = False
            if file_exist:
                return latest
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
    @profile_classmethod
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
            models.Index(fields=["pid_provider_xml", "pid_in_xml", "version"]),
        ]

    def __str__(self):
        return f"{self.pid_type} {self.pid_in_xml} {self.created}"

    @classmethod
    @profile_classmethod
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


class PidProviderXMLManager(models.Manager):
    """
    Manager customizado: aplica select_related("current_version") em toda
    consulta de PidProviderXML.objects, evitando repetir esse select_related
    manualmente em cada classmethod (get_xml_with_pre, get_record_by_pid_v3,
    select_records, public_items, mark_items_as_invalid, get_by_pid_v3, etc).

    Nota: prefetch_related("collections") NÃO entra aqui de propósito —
    prefetch_related sempre dispara uma query extra, mesmo quando
    "collections" não é usado (ex.: em _is_registered_pid, que só faz
    .exists()). Por isso ele é aplicado pontualmente em get_queryset(),
    que é o método de listagem que de fato usa collection_list.
    """

    def get_queryset(self):
        return super().get_queryset().select_related("current_version")


class PidProviderXML(BasePidProviderXML, CommonControlField, ClusterableModel):
    """
    Tem responsabilidade de garantir a atribuição do PID da versão 3,
    armazenando dados chaves que garantem a identificação do XML
    """

    proc_status = models.CharField(
        _("processing status"),
        max_length=7,
        null=True,
        blank=True,
        choices=choices.PPXML_STATUS,
        default=choices.PPXML_STATUS_TODO,
    )
    issn_electronic = models.CharField(
        _("Electronic ISSN"), max_length=10, null=True, blank=True
    )
    issn_print = models.CharField(_("Print ISSN"), max_length=10, null=True, blank=True)
    pub_year = models.CharField(
        _("publication year"), max_length=4, null=True, blank=True
    )
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
    collections = models.ManyToManyField(Collection, blank=True)

    # dados legíveis para facilitar a análise
    readable_data = models.JSONField(
        _("Readable data"), null=True, blank=True
    )

    objects = PidProviderXMLManager()

    base_form_class = CoreAdminModelForm

    panel_a = [
        FieldPanel("proc_status"),
        FieldPanel("collections", read_only=True),
        FieldPanel("issn_electronic", read_only=True),
        FieldPanel("issn_print", read_only=True),
        FieldPanel("pub_year", read_only=True),
        FieldPanel("pkg_name", read_only=True),
        FieldPanel("main_doi", read_only=True),
        FieldPanel("v3", read_only=True),
        FieldPanel("v2", read_only=True),
        FieldPanel("aop_pid", read_only=True),
        FieldPanel("available_since", read_only=True),
        FieldPanel("registered_in_core", read_only=True),
    ]
    panel_b = [
        AutocompletePanel("collections", read_only=True),
        AutocompletePanel("current_version", read_only=True),
        InlinePanel("other_pid", label=_("Other PID")),
    ]
    panel_c = [
        FieldPanel("z_surnames", read_only=True),
        FieldPanel("z_collab", read_only=True),
        FieldPanel("z_links", read_only=True),
        FieldPanel("z_partial_body", read_only=True),
        FieldPanel("readable_data", widget=ReadOnlyPrettyJSONWidget(), read_only=True),
    ]

    panels_event = [
        InlinePanel("events", label=_("Events")),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panel_a, heading=_("Identification")),
            ObjectList(panel_b, heading=_("Other PIDs")),
            ObjectList(panel_c, heading=_("Data")),
            ObjectList(panels_event, heading=_("Events")),
        ]
    )

    class Meta:
        ordering = ["-updated", "-created", "pkg_name"]
        indexes = [
            # === ID unicos ===
            models.Index(fields=["pkg_name"]),
            models.Index(fields=["v3"]),
            models.Index(fields=["v2"]),
            models.Index(
                fields=["aop_pid"],
                condition=Q(aop_pid__isnull=False),
                name="ppx_aop_pid",
            ),
            models.Index(
                fields=["main_doi"],
                condition=Q(main_doi__isnull=False),
                name="ppx_main_doi",
            ),
            # === journal ===
            models.Index(
                fields=["issn_electronic"],
                condition=Q(issn_electronic__isnull=False),
                name="ppx_issn_electronic",
            ),
            models.Index(
                fields=["issn_print"],
                condition=Q(issn_print__isnull=False),
                name="ppx_issn_print",
            ),
            # === authors ===
            models.Index(
                fields=["z_surnames"],
                condition=Q(z_surnames__isnull=False),
                name="ppx_z_surnames",
            ),
            models.Index(
                fields=["z_collab"],
                condition=Q(z_collab__isnull=False),
                name="ppx_z_collab",
            ),
            # Para queries com datas
            models.Index(fields=["-updated"]),
            models.Index(fields=["-created"]),
            # === Operacionais ===
            models.Index(fields=["proc_status"]),
            models.Index(fields=["registered_in_core"]),
            models.Index(fields=["available_since", "-updated"]),
            # === Compostos ===
            models.Index(
                fields=["issn_electronic", "elocation_id"],
                condition=Q(issn_electronic__isnull=False, elocation_id__isnull=False),
                name="ppx_elocation_id",
            ),
            models.Index(
                fields=["issn_electronic", "pub_year", "volume", "number", "suppl"],
                condition=Q(issn_electronic__isnull=False),
                name="ppx_eissue",
            ),
            models.Index(
                fields=["issn_print", "pub_year", "volume", "number", "suppl"],
                condition=Q(issn_print__isnull=False),
                name="ppx_pissue",
            ),
            models.Index(
                fields=["fpage", "fpage_seq", "lpage"],
                condition=Q(fpage__isnull=False),
                name="ppx_fpage",
            ),
            # Para otimizar queries com current_version
            models.Index(fields=["current_version"]),
        ]

    def __str__(self):
        return f"{self.pkg_name} {self.v3}"

    @property
    def collection_list(self):
        return "|".join(c.acron3 for c in self.collections.all())

    @classmethod
    def get_queryset(
        cls,
        issn_list=None,
        from_pub_year=None,
        until_pub_year=None,
        from_updated_date=None,
        until_updated_date=None,
        proc_status_list=None,
        params=None,
    ):
        params = params or {}

        q = Q()
        if issn_list:
            q = Q(issn_print__in=issn_list) | Q(issn_electronic__in=issn_list)
        if from_updated_date:
            params["updated__gte"] = from_updated_date
        if until_updated_date:
            params["updated__lte"] = until_updated_date
        if from_pub_year:
            params["pub_year__gte"] = from_pub_year
        if until_pub_year:
            params["pub_year__lte"] = until_pub_year
        if proc_status_list:
            params["proc_status__in"] = proc_status_list
        # select_related("current_version") já vem do manager;
        # prefetch_related("collections") é aplicado aqui pois este método
        # é usado em listagens que iteram collection_list.
        return cls.objects.prefetch_related("collections").filter(q, **params)

    @classmethod
    def delete_queryset(cls, qs):
        OtherPid.objects.filter(pid_provider_xml__in=qs).delete()
        qs.delete()

    @classmethod
    @profile_classmethod
    def public_items(cls, from_date):
        now = datetime.utcnow().isoformat()[:10]
        # select_related("current_version") já vem do manager
        return cls.objects.filter(
            (Q(available_since__isnull=True) | Q(available_since__lte=now))
            & (Q(created__gte=from_date) | Q(updated__gte=from_date)),
            current_version__pid_provider_xml__v3__isnull=False,
        ).iterator()

    @property
    def created_updated(self):
        return self.updated or self.created

    @property
    @profile_property
    def data(self):
        _data = {
            "v3": self.v3,
            "v2": self.v2,
            "aop_pid": self.aop_pid,
            "pkg_name": self.pkg_name,
            "finger_print": self.current_version and self.current_version.finger_print,
            "created": self.created and self.created.isoformat(),
            "updated": self.updated and self.updated.isoformat(),
            "record_status": "updated" if self.updated else "created",
            "registered_in_core": self.registered_in_core,
        }
        return _data

    @classmethod
    @profile_classmethod
    def get_xml_with_pre(cls, v3):
        try:
            # select_related("current_version") já vem do manager
            return cls.objects.get(v3=v3).xml_with_pre
        except cls.DoesNotExist:
            return None
        except Exception:
            return None

    @property
    @profile_property
    def xml_with_pre(self):
        try:
            return self.current_version.xml_with_pre
        except Exception as e:
            logging.exception(e)
            if self.proc_status != choices.PPXML_STATUS_INVALID:
                self.proc_status = choices.PPXML_STATUS_INVALID
                self.save()
            logging.info(self.proc_status)
            return None

    @cached_property
    def is_aop(self):
        if self.volume:
            return False
        if self.number:
            return False
        return True

    @property
    def data_to_compare(self):
        readable = self.readable_data or {}
        titles = readable.get("article_titles")
        body_fragment = readable.get("body_fragment")
        return {
            "article_titles": titles or self.xml_with_pre.article_titles_texts,
            "z_surnames": self.z_surnames,
            "z_collab": self.z_collab,
            "z_links": self.z_links,
            "z_partial_body": self.z_partial_body,
            "body_fragment": body_fragment or self.xml_with_pre.get_body_fragment(PARTIAL_BODY_MAX),
        }

    @classmethod
    @profile_classmethod
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
        auto_solve_pid_conflict=True,
    ):
        """
        Registra documento XML no sistema de PIDs, retornando PIDs v3, v2 e aop_pid.

        Parameters
        ----------
        xml_with_pre : XMLWithPre
            Dados XML preprocessados
        filename : str
            Nome do arquivo XML
        user : User
            Usuário responsável pelo registro
        origin_date : datetime, optional
            Data de origem do documento
        force_update : bool, optional
            Força atualização mesmo sem alterações
        is_published : bool, default False
            Status de publicação
        available_since : datetime, optional
            Data de disponibilização
        origin : str, optional
            Origem do documento
        registered_in_core : bool, optional
            Se já registrado no sistema core
        auto_solve_pid_conflict : bool, default False
            Resolve conflitos de PID automaticamente

        Returns
        -------
        dict
            Sucesso: {"v3", "v2", "aop_pid", "xml_uri", "article", "created",
                     "updated", "xml_changed", "record_status"}
            Erro: {"error_type", "error_message", "id", "filename"}

        Raises
        ------
        QueryDocumentMultipleObjectsReturnedError
            Múltiplos documentos encontrados
        RequiredPublicationYearErrorToGetPidProviderXMLError
            Ano de publicação obrigatório ausente
        RequiredISSNErrorToGetPidProviderXMLError
            ISSN obrigatório ausente
        NotEnoughParametersToGetPidProviderXMLError
            Parâmetros insuficientes para identificar documento
        """
        try:
            # outputs
            response = {}
            registered = None
            event_status = None
            error_type = None
            select_record_response = None

            # inputs
            pkg_name = filename
            input_data = None
            xml_adapter_data = None

            input_data = {}
            input_data.update(xml_with_pre.data)
            input_data.update(xml_with_pre.get_article_data())
            input_data["origin"] = origin
            response["input_data"] = input_data

            # adaptador do xml with pre
            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
            xml_adapter_data = xml_adapter.data
            response["xml_adapter_data"] = xml_adapter_data

            # consulta se documento já está registrado
            try:
                records = cls.select_records(xml_adapter)
                select_record_response = cls.select_record(xml_adapter, records)
                try:
                    registered = select_record_response.pop("registered")
                except KeyError:
                    unmatched_items = select_record_response.get("unmatched_items")
                    if unmatched_items:
                        raise exceptions.UnmatchedPidProviderXMLError
                    raise cls.DoesNotExist
                event_status = "updated"
                if select_record_response.get("matched_items"):
                    response["select_record_response"] = select_record_response
            except cls.DoesNotExist as exc:
                registered = None
                event_status = "created"
            except (cls.MultipleObjectsReturned, exceptions.UnmatchedPidProviderXMLError) as exc:
                event_status = "unmatched"
                response["select_record_response"] = select_record_response
                raise exceptions.QueryDocumentMultipleObjectsReturnedError(exc)
            except (
                exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError,
                exceptions.RequiredISSNErrorToGetPidProviderXMLError,
                exceptions.NotEnoughParametersToGetPidProviderXMLError,
            ) as exc:
                event_status = "bad_request"
                raise exc

            # valida os PIDs do XML
            # - não podem ter conflito com outros registros
            # - identifica mudança
            try:
                response["xml_changed"] = cls.complete_missing_xml_pids(
                    xml_adapter, registered, auto_solve_pid_conflict
                )
            except PidProviderXMLPidV3ConflictError as exc:
                event_status = "conflict"
                raise exc

            # analisa se continua o registro
            try:
                PidProviderXML.is_updated(
                    xml_with_pre,
                    registered,
                    force_update,
                    origin_date,
                    registered_in_core,
                )
                registered = cls._save(
                    registered,
                    xml_adapter,
                    user,
                    origin_date,
                    available_since,
                    registered_in_core,
                )
                # data to return
                response.update(registered.data)
            except exceptions.ForbiddenPidProviderXMLRegistrationError:
                event_status = "forbidden"
                raise
            except exceptions.SkipSavePidProviderXML:
                event_status = "skipped"
                response["skipped"] = True
                response.update(registered.data)
                # do not raise
        except Exception as exc:
            event_status = event_status or "error"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_type = str(type(exc))
            response.update({
                "error_msg": str(exc),
                "error_type": error_type,
                "traceback": traceback.format_exc()
            })
        finally:            
            response["event_status"] = event_status
            if error_type or (select_record_response or {}).get("matched_items"):
                PidProviderXMLRegistration.record(
                    user=user,
                    pid_provider_xml=registered,
                    pkg_name=pkg_name,
                    event_status=event_status,
                    detail=response,
                )
        return response

    @classmethod
    @profile_classmethod
    def complete_missing_xml_pids(
        cls, xml_adapter, registered, auto_solve_pid_conflict
    ):
        xml_changed = {}
        xml_with_pre = xml_adapter.xml_with_pre

        if xml_with_pre.v3:
            cls.is_valid_pid_len(xml_with_pre.v3, "pid_v3")
        if xml_with_pre.v2:
            cls.is_valid_pid_len(xml_with_pre.v2, "pid_v2")
        if xml_with_pre.aop_pid:
            cls.is_valid_pid_len(xml_with_pre.aop_pid, "aop_pid")

        valid_pid = cls.get_valid_pid_v3(
            xml_adapter,
            registered_pid=registered and registered.v3,
            auto_solve_pid_conflict=auto_solve_pid_conflict,
        )

        if valid_pid != xml_with_pre.v3:
            xml_with_pre.v3 = valid_pid
            xml_changed["pid_v3"] = valid_pid

        if registered:
            if not xml_with_pre.v2 and registered.v2:
                xml_with_pre.v2 = registered.v2
                xml_changed["pid_v2"] = registered.v2
            if not xml_with_pre.aop_pid and registered.aop_pid:
                xml_with_pre.aop_pid = registered.aop_pid
                xml_changed["aop_pid"] = registered.aop_pid
        return xml_changed

    @classmethod
    @profile_classmethod
    def get_valid_pid_v3(
        cls, xml_adapter, registered_pid, auto_solve_pid_conflict=False
    ):
        # Se XML PID foi fornecido e é diferente do registrado:
        xml_pid = xml_adapter.v3
        if xml_pid and xml_pid != registered_pid:
            # Verifica se o XML PID já está em uso por outro documento.
            try:
                # verificar se xml_adapter.v3 pertence a outro xml
                cls.get_record_by_pid_v3(xml_adapter)
                # pertence a xml_adapter
                return xml_pid
            except cls.DoesNotExist:
                # não pertence a nenhum xml
                return xml_pid
            except PidProviderXMLPidV3ConflictError:
                # pertence a um xml diferente de xml_adapter
                if not auto_solve_pid_conflict:
                    # rejeita o uso deste pid
                    raise
                # ignora 
        # XML PID não fornecido, ou igual ao registrado
        # ou em conflito sem exceção
        # retorna o PID registrado ou gera um novo.
        return registered_pid or cls._get_unique_v3()

    @classmethod
    @profile_classmethod
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
            registered_changed = registered.check_registered_pids_changed(
                xml_adapter.xml_with_pre
            )
            registered.updated_by = user
        else:
            registered = cls()
            registered.creator = user
            registered_changed = None
 
        registered.proc_status = choices.PPXML_STATUS_TODO
        registered._add_dates(xml_adapter, origin_date, available_since)
        registered._add_data(xml_adapter, registered_in_core)
        registered._add_journal(xml_adapter)
        registered._add_issue(xml_adapter)
 
        registered.save()
 
        if registered_changed:
            registered._add_other_pid(registered_changed, user)
        registered._add_current_version(xml_adapter.xml_with_pre, user)
 
        registered.add_collections(xml_adapter)
        return registered

    def add_collections(self, xml_adapter):
        q = Q()
        issn_print = xml_adapter.journal_issn_print
        issn_electronic = xml_adapter.journal_issn_electronic

        try:
            Collection.objects.filter(scielojournal__isnull=True).exists()
            issn_path = "scielojournal__journal__official"
        except FieldError:
            issn_path = "journalproc__journal__official_journal"

        if issn_print:
            q |= Q(**{f"{issn_path}__issn_print": issn_print})
        if issn_electronic:
            q |= Q(**{f"{issn_path}__issn_electronic": issn_electronic})

        for collection in Collection.objects.filter(q):
            self.collections.add(collection)

    @staticmethod
    def is_updated(
        xml_with_pre, registered, force_update, origin_date, registered_in_core
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

        if registered_in_core and not registered.registered_in_core:
            logging.info(
                f"Do not skip update: need to update registered.registered_in_core=True"
            )
            return

        # verifica se é necessário atualizar
        if registered.is_equal_to(xml_with_pre):
            # XML fornecido é igual ao registrado, não precisa continuar
            logging.info(f"Skip update: equal")
            raise exceptions.SkipSavePidProviderXML

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
            raise exceptions.SkipSavePidProviderXML

    @profile_method
    def is_equal_to(self, xml_with_pre):
        return bool(
            self.current_version and self.current_version.is_equal_to(xml_with_pre)
        )

    @classmethod
    @profile_classmethod
    def select_records(cls, xml_adapter):
        """
        Gera pares (label, lista_de_candidatos) para cada estratégia de
        correspondência, do mais específico ao mais genérico.

        Cada branch é materializada (list(...)) uma única vez aqui, para
        que o consumidor (select_record) nunca precise avaliar a queryset
        mais de uma vez (evita repetir .exists() + .count() + iteração,
        que geram queries separadas no banco). Por ser um generator, uma
        branch só é construída e avaliada quando o consumidor de fato
        solicita o próximo item — se a primeira branch já resolver, as
        demais nunca chegam a rodar no banco.
        """
        qbuilder = QueryBuilderPidProviderXML(xml_adapter)
        qbuilder.validate_input_data()

        # select_related("current_version") já vem do manager
        objects = cls.objects.all()

        # 1) correspondência direta por identificadores
        yield "ids", list(objects.filter(qbuilder.identifier_queries))

        selected_journal = objects.filter(qbuilder.issn_query)

        # 2) journal + issue + dados do artigo
        yield (
            "journal-issue-article",
            list(
                selected_journal.filter(
                    Q(**qbuilder.issue_params) & qbuilder.article_data_query
                )
            ),
        )

        # 3) journal + dados do artigo
        yield "journal-article", list(selected_journal.filter(qbuilder.article_data_query))

    @staticmethod
    def select_record(xml_adapter, selection_results):
        """
        Consome os pares (label, lista_de_candidatos) produzidos por
        select_records. As listas já vêm materializadas, então aqui só
        checamos truthiness (nunca .exists()/.count() sobre queryset).
        """
        unmatched_items = {}
        xml_adapter_data_to_compare = xml_adapter.get_data_to_compare()
        for label, results in selection_results:
            if not results:
                continue

            result = PidProviderXML.get_best_match(results, xml_adapter_data_to_compare)

            matched = result.get("matched")
            unmatched = result.get("unmatched")
            registered = result.get("registered")
            if registered:
                response = {
                    "total_results": len(results),
                    "registered": registered,
                }
                if matched:
                    response["matched_items"] = {label: matched}
                if unmatched:
                    response["unmatched_items"] = {label: unmatched}
                return response

            if unmatched:
                unmatched_items[label] = unmatched

        if unmatched_items:
            return {"unmatched_items": unmatched_items}
        return {}

    @classmethod
    @profile_classmethod
    def get_record_by_pid_v3(cls, xml_adapter):
        # tenta procurar pelo pid_v3
        if not xml_adapter.v3:
            raise ValueError("get_record_by_pid_v3: XML has not pid v3")
        xml_pid_v3 = xml_adapter.v3
        # select_related("current_version") já vem do manager
        results = cls.objects.filter(
            Q(v3=xml_pid_v3) | Q(other_pid__pid_in_xml=xml_pid_v3)
        )
        if not results.exists():
            # pid v3 é inédito
            raise cls.DoesNotExist
        
        xml_adapter_data_to_compare = xml_adapter.get_data_to_compare()
        result = PidProviderXML.get_best_match(results, xml_adapter_data_to_compare)
        registered = result.get("registered")
        if not registered:
            xml_data = xml_adapter.xml_with_pre.get_article_data(PARTIAL_BODY_MAX)
            items = [item.data for item in results]
            raise PidProviderXMLPidV3ConflictError(
                _(f"{xml_pid_v3} belongs to {items}, not to {xml_data}")
            )
        return registered

    @staticmethod
    def get_best_match(results, xml_adapter_data):
        """
        Compara uma lista de candidatos (PidProviderXML) com os dados do XML
        recebido e classifica os candidatos por similaridade.

        Parameters
        ----------
        results : list[PidProviderXML]
            Lista JÁ MATERIALIZADA (não queryset) de candidatos a comparar.
        xml_adapter_data : dict
            Dados de comparação do XML de entrada, ou seja, o retorno de
            ``xml_adapter.get_data_to_compare()``.

        Returns
        -------
        dict
            Todas as chaves abaixo são OPCIONAIS — só aparecem quando há
            conteúdo para elas. Use ``.get(...)`` ou ``"chave" in result``
            ao consumir o retorno, nunca acesso direto.

            - ``"unmatched"``: presente apenas se houver ao menos 1
            candidato com ``percentual_score`` <= 0.6. Lista de
            ``item.data`` desses candidatos.
            - ``"registered"``: presente apenas se houver ao menos 1
            candidato aprovado (score > 0.6). Contém o OBJETO
            ``PidProviderXML`` (não o dict ``.data``) do candidato com
            maior score — em caso de empate, o critério de desempate é
            ``updated`` mais recente e, em seguida, maior ``id``.
            - ``"matched"``: presente apenas se houver 2 OU MAIS candidatos
            aprovados. Contém ``item.data`` dos candidatos aprovados
            EXCLUINDO o que já está em ``"registered"`` (ou seja, é a
            lista de aprovados a partir do 2º colocado), na mesma ordem
            de score decrescente.
        """
        detail = {}
        found = []
        items = {}
        for item in results:
            item_data = item.data_to_compare
            response = compare(item_data, xml_adapter_data)
            items[item.id] = item
            found.append((response["percentual_score"], item.updated.isoformat(), item.id))

        found = sorted(found, reverse=True)
        matched = []
        unmatched = []
        for percentual_score, updated, item_id in found:
            if percentual_score > 0.6:
                matched.append(items[item_id].data)
            else:
                unmatched.append(items[item_id].data)
        if matched:
            detail["registered"] = items[found[0][-1]]
            if len(matched) > 1:
                detail["matched"] = matched[1:]
        if unmatched:
            detail["unmatched"] = unmatched
        return detail

    @profile_method
    def _add_data(self, xml_adapter, registered_in_core):
        self.registered_in_core = bool(registered_in_core)

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

        self.readable_data = xml_adapter.xml_with_pre.get_article_data()

    @profile_method
    def _add_dates(self, xml_adapter, origin_date, available_since):
        # evita que artigos WIP fique disponíveis antes de estarem públicos
        try:
            # Usa get_complete_publication_date para evitar logs de erro do
            # packtools quando a data de publicação no XML é incompleta
            # (ex.: <pub-date> apenas com <year> e <season>, sem mes/dia).
            # Mesmo padrão adotado em proc/models.py e package/models.py.
            self.available_since = available_since or (
                xml_adapter.xml_with_pre.get_complete_publication_date()
            )
        except Exception as e:
            # packtools error
            self.available_since = origin_date
        self.origin_date = origin_date

    @profile_method
    def _add_journal(self, xml_adapter):
        self.issn_electronic = xml_adapter.journal_issn_electronic
        self.issn_print = xml_adapter.journal_issn_print

    @profile_method
    def _add_issue(self, xml_adapter):
        self.volume = zero_to_none(xml_adapter.volume)
        self.number = zero_to_none(xml_adapter.number)
        self.suppl = xml_adapter.suppl
        self.pub_year = xml_adapter.pub_year or xml_adapter.article_pub_year

    @profile_method
    def _add_current_version(self, xml_with_pre, user, delete=False):
        if delete:
            try:
                self.current_version.delete()
            except Exception as e:
                pass

        self.current_version = XMLVersion.get_or_create(user, self, xml_with_pre)
        self.save()

    @profile_method
    def check_registered_pids_changed(self, xml_with_pre):
        registered_changed = []
        if self.v3 != xml_with_pre.v3:
            registered_changed.append(
                {
                    "pid_type": "pid_v3",
                    "pid_in_xml": xml_with_pre.v3,
                    "version": self.current_version,
                    "registered": self.v3,
                }
            )
        if self.v2 != xml_with_pre.v2:
            registered_changed.append(
                {
                    "pid_type": "pid_v2",
                    "pid_in_xml": xml_with_pre.v2,
                    "version": self.current_version,
                    "registered": self.v2,
                }
            )
        if self.aop_pid != xml_with_pre.aop_pid:
            registered_changed.append(
                {
                    "pid_type": "aop_pid",
                    "pid_in_xml": xml_with_pre.aop_pid,
                    "version": self.current_version,
                    "registered": self.aop_pid,
                }
            )
        return registered_changed

    @profile_method
    def _add_other_pid(self, registered_changed, user):
        if not registered_changed:
            return
        for change_args in registered_changed:
            change_args["pid_in_xml"] = change_args.pop("registered")
            change_args["user"] = user
            change_args["pid_provider_xml"] = self
            OtherPid.get_or_create(**change_args)
        self.other_pid_count = self.other_pid.count()
        self.save(update_fields=["other_pid_count"])

    @classmethod
    @profile_classmethod
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
    @profile_classmethod
    def _is_registered_pid(cls, v2=None, v3=None, aop_pid=None):
        if v3:
            qs = Q(v3=v3) | Q(other_pid__pid_in_xml=v3)
        elif v2:
            qs = Q(v2=v2) | Q(other_pid__pid_in_xml=v2)
        elif aop_pid:
            qs = Q(v2=aop_pid) | Q(other_pid__pid_in_xml=aop_pid) | Q(aop_pid=aop_pid)
        else:
            return None
        return cls.objects.filter(qs).exists()

    @staticmethod
    @profile_staticmethod
    def is_valid_pid_len(value, pid_type):
        if value and len(value) == 23:
            return True
        raise ValueError(f"Invalid {pid_type} length: {value}")

    @classmethod
    @profile_classmethod
    def is_registered(
        cls,
        xml_with_pre,
    ):
        """
        Verifica se há necessidade de registrar, se está registrado e é igual

        Parameters
        ----------
        xml_with_pre : XMLWithPre

        """
        try:
            select_record_response = None
            response = {}
            response["input_data"] = xml_with_pre.data

            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
            response["xml_adapter_data"] = xml_adapter.data

            try:
                records = cls.select_records(xml_adapter)
                select_record_response = cls.select_record(xml_adapter, records)
                try:
                    registered = select_record_response.pop("registered")
                except KeyError:
                    unmatched_items = select_record_response.get("unmatched_items")
                    if unmatched_items:
                        raise exceptions.UnmatchedPidProviderXMLError
                    raise cls.DoesNotExist
                matched_items = select_record_response.get("matched_items")
                if matched_items:
                    response["select_record_response"] = select_record_response
            except cls.DoesNotExist as exc:
                response.update(
                    {"filename": xml_with_pre.filename, "registered": False}
                )
                return response
            except (cls.MultipleObjectsReturned, exceptions.UnmatchedPidProviderXMLError) as exc:
                response["select_record_response"] = select_record_response
                raise
            except (
                exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError,
                exceptions.RequiredISSNErrorToGetPidProviderXMLError,
                exceptions.NotEnoughParametersToGetPidProviderXMLError,
            ) as exc:
                raise exc
            response["registered"] = True
            response.update(registered.data)
            response["is_equal"] = registered.is_equal_to(xml_with_pre)
            return response
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            response.update({
                "error_msg": str(e),
                "error_type": str(type(e)),
                "traceback": traceback.format_exc()
            })
            return response
    
    @classmethod
    def get_by_pid_v3(cls, pid_v3, partial_pid_v2=None, pid_v2=None):
        params = {}
        if pid_v3:
            params["v3"] = pid_v3
        if pid_v2:
            params["v2"] = pid_v2
        if partial_pid_v2:
            params["v2__contains"] = partial_pid_v2
        # select_related("current_version") já vem do manager
        try:
            return cls.objects.get(**params)
        except cls.MultipleObjectsReturned as e:
            return cls.objects.filter(**params).order_by("-updated").first()

    @classmethod
    @profile_classmethod
    def fix_pid_v2(cls, user, pid_v3, correct_pid_v2):
        try:
            item = cls.get_by_pid_v3(pid_v3)
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

    @profile_method
    def mark_as_waiting(self):
        if self.proc_status != choices.PPXML_STATUS_WAIT:
            self.proc_status = choices.PPXML_STATUS_WAIT
            self.save()

    @profile_method
    def mark_as_done(self):
        if self.proc_status != choices.PPXML_STATUS_DONE:
            self.proc_status = choices.PPXML_STATUS_DONE
            self.save()

    @classmethod
    @profile_classmethod
    def mark_items_as_invalid(cls, issns):
        # select_related("current_version") já vem do manager
        # (necessário aqui pois o loop acessa item.xml_with_pre, que usa
        # self.current_version)
        items = cls.objects.filter(
            Q(issn_print__in=issns) | Q(issn_electronic__in=issns),
        )
        items_to_update = []
        for item in items.iterator():
            try:
                valid = bool(item.xml_with_pre)
            except Exception as e:
                valid = False
            if not valid:
                item.proc_status = choices.PPXML_STATUS_INVALID
                items_to_update.append(item)
        cls.objects.bulk_update(items_to_update, ["proc_status"], batch_size=100)

    @classmethod
    @profile_classmethod
    def find_duplicated_pkg_names(cls, issns):
        # Busca em ambos os campos de ISSN
        duplicates = (
            cls.objects.filter(Q(issn_print__in=issns) | Q(issn_electronic__in=issns))
            .exclude(pkg_name__isnull=True)
            .exclude(pkg_name="")
            .exclude(
                proc_status__in=[
                    choices.PPXML_STATUS_DUPLICATED,
                    choices.PPXML_STATUS_INVALID,
                ]
            )
            .values("pkg_name")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )
        return list(set(item["pkg_name"] for item in duplicates))

    @classmethod
    @profile_classmethod
    def mark_items_as_duplicated(cls, issns):
        ppx_duplicated_pkg_names = PidProviderXML.find_duplicated_pkg_names(issns)
        if not ppx_duplicated_pkg_names:
            return
        cls.objects.filter(pkg_name__in=ppx_duplicated_pkg_names).exclude(
            proc_status=choices.PPXML_STATUS_DUPLICATED
        ).update(
            proc_status=choices.PPXML_STATUS_DUPLICATED,
        )
        return ppx_duplicated_pkg_names

    @classmethod
    @profile_classmethod
    def deduplicate_items(cls, user, issns):
        """
        Corrige todos os artigos marcados como DATA_STATUS_DUPLICATED com base nos ISSNs fornecidos.

        Args:
            issns: Lista de ISSNs para verificar duplicatas.
            user: Usuário que está executando a operação.
        """
        duplicated_pkg_names = cls.find_duplicated_pkg_names(issns)
        for pkg_name in duplicated_pkg_names:
            cls.fix_duplicated_pkg_name(pkg_name, user)
        return duplicated_pkg_names

    @classmethod
    @profile_classmethod
    def fix_duplicated_pkg_name(cls, pkg_name, user):
        """
        Corrige items marcados como PPXML_STATUS_DUPLICATED com base no pkg_name fornecido.

        Args:
            pkg_name: Nome do pacote para verificar duplicatas.
            user: Usuário que está executando a operação.

        Returns:
            int: Número de items atualizados.
        """
        try:
            # select_related("current_version") já vem do manager.
            # prefetch_related com Prefetch + to_attr é necessário aqui
            # porque o loop chama item.other_pid.filter(pid_type="pid_v3"),
            # e um .filter() sobre manager relacionado ignora o cache do
            # prefetch_related simples (só .all() usa o cache) — por isso
            # a filtragem precisa estar dentro do próprio Prefetch.
            items = cls.objects.prefetch_related(
                Prefetch(
                    "other_pid",
                    queryset=OtherPid.objects.filter(pid_type="pid_v3"),
                    to_attr="pid_v3_others",
                )
            ).filter(pkg_name=pkg_name)
            if items.count() <= 1:
                return 0

            most_recent_item = items.order_by("-updated").first()
            if not most_recent_item:
                return 0

            logging.info(
                f"Fixing duplicated PidProviderXML pkg_name={pkg_name} with {items.count()} items. Keeping {most_recent_item.v3} as the correct one."
            )
            # Mantém o artigo mais recente como o correto
            most_recent_item.proc_status = choices.PPXML_STATUS_DEDUPLICATED
            most_recent_item.save()

            for item in items.exclude(id=most_recent_item.id):
                for other_pid in item.pid_v3_others:
                    OtherPid.get_or_create(
                        user=user,
                        pid_type=other_pid.pid_type,
                        pid_in_xml=other_pid.pid_in_xml,
                        # Nota: OtherPid não tem campo current_version, e
                        # sim `version` — corrigido aqui (era
                        # other_pid.current_version, que não existe no
                        # modelo e lançaria AttributeError).
                        version=other_pid.version,
                        pid_provider_xml=most_recent_item,
                    )
                OtherPid.get_or_create(
                    user=user,
                    pid_type="pid_v3",
                    pid_in_xml=item.v3,
                    version=item.current_version,
                    pid_provider_xml=most_recent_item,
                )
        except Exception as exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=exception,
                exc_traceback=exc_traceback,
                action="pid_provider.models.PidProviderXML.fix_duplicated_pkg_name",
                detail=pkg_name,
            )

    def fix_pkg_name(self, pkg_name):
        if not pkg_name:
            pkg_name = self.xml_with_pre.sps_pkg_name
        if pkg_name and self.pkg_name != pkg_name:
            self.pkg_name = pkg_name
            self.save()
            return True
        return False


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
    @profile_staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return FixPidV2.objects.filter(pid_provider_xml__v3__icontains=search_term)

    @profile_method
    def autocomplete_label(self):
        return f"{self.pid_provider_xml.v3}"

    @classmethod
    @profile_classmethod
    def get(cls, pid_provider_xml=None):
        if pid_provider_xml:
            return cls.objects.get(pid_provider_xml=pid_provider_xml)
        raise ValueError("FixPidV2.get requires pid_v3")

    @classmethod
    @profile_classmethod
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
    @profile_classmethod
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
    @profile_classmethod
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


def xml_url_zipfile_path(instance, filename):
    """
    Generate the upload path for XMLURL zipfile.
    
    Args:
        instance: XMLURL instance
        filename: Name of the file
        
    Returns:
        Path string for file upload
    """
    # Use URL hash to create a unique subdirectory
    url_hash = abs(hash(instance.url)) % (10 ** 8)
    return f"pid_provider/xmlurl/{url_hash}/{filename}"


class XMLURL(CommonControlField):
    """
    Model to store URLs that experienced failures and should be retried in the future.

    This model tracks URLs that failed during processing, along with their status
    and associated article PID, enabling retry mechanisms to reprocess them later.

    Fields:
        url: URLField - The URL that needs to be retried
        status: CharField - To control the request status (e.g., "pending", "failed", "retrying")
        pid: CharField - Article PID associated with this URL
        zipfile: FileField - Compressed XML content retrieved from the URL
        detail: JSONField
        is_public: BooleanField - Whether the document is public (derived from item status)
    """

    url = models.URLField(
        _("URL"), max_length=500, null=False, blank=False
    )
    status = models.CharField(
        _("Status"), max_length=50, null=True, blank=True,
        choices=choices.XMLURL_STATUS,
    )
    pid = models.CharField(
        _("Article PID"), max_length=23, null=True, blank=True
    )
    zipfile = models.FileField(
        _("ZIP File"), upload_to=xml_url_zipfile_path, null=True, blank=True, max_length=300,
    )
    detail = models.JSONField(
        _("Detail"), null=True, blank=True
    )
    is_public = models.BooleanField(
        _("Is Public"), null=True, blank=True, default=None
    )

    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("url"),
        FieldPanel("status"),
        FieldPanel("pid"),
        FieldPanel("zipfile"),
        FieldPanel("detail", widget=ReadOnlyPrettyJSONWidget()),
        FieldPanel("is_public"),
    ]

    class Meta:
        ordering = ["-updated", "-created"]
        verbose_name = _("XML URL")
        verbose_name_plural = _("XML URLs")

        indexes = [
            models.Index(fields=["url"]),
            models.Index(fields=["status"]),
            models.Index(fields=["pid"]),
            models.Index(fields=["is_public"], name="pid_provide_is_public_idx"),
        ]

    def __str__(self):
        return f"{self.url} - {self.status}"

    @classmethod
    def get(cls, url=None):
        if url:
            return cls.objects.get(url=url)
        raise ValueError("XMLURL.get() requires a url parameter")

    @classmethod
    def create(
        cls,
        user,
        url=None,
        status=None,
        pid=None,
        detail=None,
        is_public=None,
    ):
        try:
            obj = cls()
            obj.url = url
            obj.status = status
            obj.pid = pid
            obj.detail = detail
            obj.is_public = is_public
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(url)

    @classmethod
    def create_or_update(
        cls,
        user,
        url=None,
        status=None,
        pid=None,
        detail=None,
        is_public=None,
    ):
        try:
            obj = cls.get(url=url)
            obj.updated_by = user
            if status is not None:
                obj.status = status
            if pid is not None:
                obj.pid = pid
            if detail is not None:
                obj.detail = detail
            if is_public is not None:
                obj.is_public = is_public
            obj.save()
            return obj
        except cls.DoesNotExist:
            return cls.create(
                user,
                url,
                status,
                pid,
                detail,
                is_public=is_public,
            )

    def save_file(self, xml_content, filename=None):
        """
        Create a zip file from XML content and save it to the zipfile field.

        Args:
            xml_content: str or bytes - The XML content to compress
            filename: str - Optional filename for the XML inside the zip (defaults to 'content.xml')

        Returns:
            bool - True if file was saved successfully, False otherwise
        """
        try:
            # Convert string to bytes if needed
            if isinstance(xml_content, str):
                xml_content = xml_content.encode('utf-8')

            # Create in-memory zip file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Use provided filename or default
                xml_filename = filename or 'content.xml'
                zip_file.writestr(xml_filename, xml_content)

            # Save the zip file to the model
            zip_filename = f"{self.pid or 'unknown'}_{self.pk or 'new'}.zip"
            self.zipfile.save(zip_filename, ContentFile(zip_buffer.getvalue()), save=True)

            return True
        except Exception as e:
            logging.error(f"Error saving zip file for XMLURL {self.url}: {e}")
            return False
        
    @classmethod
    def record(
        cls,
        user,
        url,
        document_item,
        exception=None,
        traceback_msg=None,
        response=None,
        xml_with_pre=None,
        is_public=None,
        params=None,
    ):
        detail = {
            "params": params,
            "document_item": document_item,
        }
        if exception is not None:
            detail["exception"] = {
                "error_message": str(exception),
                "error_type": str(type(exception)),
            }
        if traceback_msg is not None:
            detail["traceback"] = traceback_msg
        if response is not None:
            detail["response"] = response
        status = XMLURL.get_status(xml_with_pre, response)
        pid = (response or {}).get("v3")

        if is_public is None and document_item:
            try:
                is_public = document_item["status"]
            except KeyError:
                # não é possível saber se está publicado ou não, mantém None
                pass

        xmlurl_obj = cls.create_or_update(
            user=user,
            url=url,
            status=status,
            pid=pid,
            detail=detail,
            is_public=is_public,
        )
        if xml_with_pre:
            xmlurl_obj.save_file(xml_with_pre.tostring(), filename=xml_with_pre.sps_pkg_name+".xml")
        return xmlurl_obj
    
    @property
    def data(self):
        detail = self.detail
        if detail.get("response"):
            return detail.get("response")
        
        data = {}
        data.update(detail.get("exception") or {})
        try:
            data["traceback"] = detail["traceback"]
        except KeyError:
            pass
        return data
        
    @staticmethod
    def get_status(xml_with_pre, response):
        if not xml_with_pre:
            return choices.XMLURL_STATUS_XML_FETCH_FAILED
        if not response:
            return choices.XMLURL_STATUS_UNEXPECTED_FAILURE
        if (
            response.get("error") or 
            response.get("error_type") or 
            response.get("error_msg") or
            response.get("error_message")
        ):
            return choices.XMLURL_STATUS_PID_PROVIDER_XML_FAILED
        return choices.XMLURL_STATUS_SUCCESS


class XMLEvent(BaseEvent, CommonControlField):
    """
    Model to log events related to XML processing in the PID Provider system.

    This model captures various events that occur during the processing of XML data,
    such as registration attempts, validation errors, and other significant actions,
    along with relevant details for debugging and monitoring purposes.

    Attributes:
        name (CharField): Name of the event.
        detail (JSONField): Detailed information about the event.
        created (DateTimeField): Timestamp when the event was created.
        completed (BooleanField): Indicates if the event has been completed.
        ppxml (ParentalKey): Reference to the related PidProviderXML instance.

    Methods:
        data (property): Returns a dictionary with the event's name, detail, and creation timestamp.
        create (classmethod): Creates and saves a new XMLEvent instance.
        finish: Marks the event as completed and optionally updates details, errors, or exceptions.
    """
    ppxml = ParentalKey(
        PidProviderXML, on_delete=models.CASCADE, related_name="events"
    )

    @classmethod
    def register(cls, ppxml, name, detail=None, errors=None, exceptions=None):
        obj = cls()
        obj.ppxml = ppxml
        obj.name = name
        completed = bool(not errors and not exceptions)
        obj.finish(completed=completed, detail=detail, errors=errors, exceptions=exceptions)
        return obj


# -----------------------------------------------------------------------------
# [models.py] MODELO NOVO — PidProviderXMLRegistration
# Auditoria por documento. Grava SEMPRE (created/updated/skipped/forbidden/
# conflict/unmatched/error). FK nullable (unmatched/error podem não ter PPX).
# -----------------------------------------------------------------------------
class PidProviderXMLRegistration(CommonControlField):
    LIGHTWEIGHT_STATUSES = {"created", "updated", "skip_update"}

    EVENT_CREATED = "created"
    EVENT_UPDATED = "updated"
    EVENT_SKIPPED = "skipped"
    EVENT_FORBIDDEN = "forbidden"
    EVENT_CONFLICT = "conflict"
    EVENT_UNMATCHED = "unmatched"
    EVENT_ERROR = "error"
    EVENT_BAD_REQUEST = "bad_request"

    EVENT_STATUS_CHOICES = (
        (EVENT_CREATED, "created"),
        (EVENT_UPDATED, "updated"),
        (EVENT_SKIPPED, "skipped"),
        (EVENT_FORBIDDEN, "forbidden"),
        (EVENT_CONFLICT, "conflict"),
        (EVENT_UNMATCHED, "unmatched"),
        (EVENT_BAD_REQUEST, "bad_request"),
        (EVENT_ERROR, "error"),
    )

    pid_provider_xml = models.ForeignKey(
        PidProviderXML,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registration_events",
    )
    pkg_name = models.CharField(
        _("Package name"), max_length=100, null=True, blank=True
    )
    event_status = models.CharField( 
        _("Event status"),
        max_length=15,
        null=True,
        blank=True,
        choices=EVENT_STATUS_CHOICES,
    )
    detail = models.JSONField(_("Detail"), null=True, blank=True)

    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("event_status", read_only=True),
        FieldPanel("pkg_name", read_only=True),
        AutocompletePanel("pid_provider_xml", read_only=True),
        FieldPanel("detail", widget=ReadOnlyPrettyJSONWidget(), read_only=True),
    ]

    class Meta:
        ordering = ["-created"]
        verbose_name = _("PidProviderXML Registration")
        verbose_name_plural = _("PidProviderXML Registrations")
        indexes = [
            models.Index(fields=["pkg_name"]),
            models.Index(fields=["event_status"]),
            models.Index(fields=["-created"]),
            models.Index(fields=["pid_provider_xml"]),
        ]

    def __str__(self):
        return f"{self.pkg_name} {self.event_status} {self.created}"

    @staticmethod
    def _serialize_detail(detail):
        """
        O detail do detail contém o objeto PidProviderXML em
        detail['registered']. Para gravar em JSON, troca pelo v3/id.
        """
        if not detail:
            return None
        data = dict(detail)
        registered = data.get("registered")
        if registered is not None and hasattr(registered, "v3"):
            data["registered"] = {"id": registered.id, "v3": registered.v3}
        return data

    @classmethod
    def record(cls, user, event_status, pid_provider_xml=None, pkg_name=None,
            detail=None):
        try:
            obj = cls()
            obj.creator = user
            obj.pid_provider_xml = pid_provider_xml
            obj.pkg_name = pkg_name or (pid_provider_xml and pid_provider_xml.pkg_name)
            obj.event_status = event_status
            if event_status not in cls.LIGHTWEIGHT_STATUSES:
                obj.detail = cls._serialize_detail(detail)
            obj.save()
            return obj
        except Exception as e:
            logging.exception(f"Unable to record PidProviderXMLRegistration: {e}")
            return None
