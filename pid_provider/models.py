import json
import logging
import os
import sys
import traceback
from datetime import datetime
from functools import lru_cache, cached_property
from zlib import crc32

from django.core.files.base import ContentFile
from django.db import IntegrityError, models
from django.db.models import Q, Count, Min
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from packtools.sps.pid_provider import v3_gen, xml_sps_adapter
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from collection.models import Collection
from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from core.utils.profiling_tools import (  # ajuste o import conforme sua estrutura
    profile_classmethod,
    profile_method,
    profile_property,
    profile_staticmethod,
)
from core.utils.similarity import how_similar
from pid_provider import choices, exceptions
from pid_provider.query_params import (
    get_score,
    zero_to_none,
    QueryBuilderPidProviderXML,
)
from tracker.models import BaseEvent, EventSaveError, UnexpectedEvent

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
    file = models.FileField(upload_to=xml_directory_path, null=True, blank=True)
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
            if not os.path.isfile(latest.file.path):
                try:
                    filename = xml_with_pre.sps_pkg_name
                except Exception as e:
                    filename = pid_provider_xml.v3
                latest.save_file(
                    f"{filename}.xml",
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
        FieldPanel("z_surnames"),
        FieldPanel("z_collab"),
        FieldPanel("z_links"),
        FieldPanel("z_partial_body"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panel_a, heading=_("Identification")),
            ObjectList(panel_b, heading=_("Other PIDs")),
            ObjectList(panel_c, heading=_("Data")),
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
    def article_pid_suffix_source(self):
        try:
            return self.xml_with_pre.get_article_pid_suffix_source()
        except AttributeError:
            return self.elocation_id or self.fpage or self.xml_with_pre.order
    
    def get_article_pid_suffix(self):
        data = self.article_pid_suffix_source
        if not data:
            data = self.pkg_name.split("-")[-1]
        return string_to_5_digits(data)

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
        return cls.objects.filter(q, **params)

    @classmethod
    @profile_classmethod
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
            # Usar select_related para evitar query extra ao acessar current_version
            return cls.objects.select_related("current_version").get(v3=v3).xml_with_pre
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
            input_data = None
            xml_adapter_data = None

            response = {}
            response["input_data"] = xml_with_pre.data
            response["input_data"].update({"origin": origin})

            # adaptador do xml with pre
            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
            response["xml_adapter_data"] = xml_adapter.data

            # consulta se documento já está registrado
            try:
                records = cls.get_records(xml_adapter)
                registered = cls.get_record(xml_adapter, records=records)
            except cls.DoesNotExist as exc:
                registered = None
            except (cls.MultipleObjectsReturned, exceptions.UnmatchedPidProviderXMLError) as exc:
                response["records"] = [item.data for item in records]
                raise exceptions.QueryDocumentMultipleObjectsReturnedError(exc)
            except (
                exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError
            ) as exc:
                raise exc
            except exceptions.RequiredISSNErrorToGetPidProviderXMLError as exc:
                raise exc
            except exceptions.NotEnoughParametersToGetPidProviderXMLError as exc:
                raise exc

            # valida os PIDs do XML
            # - não podem ter conflito com outros registros
            # - identifica mudança
            response["xml_changed"] = cls.complete_missing_xml_pids(
                xml_adapter, registered, auto_solve_pid_conflict
            )

            # analisa se continua o registro
            updated_data = cls.is_updated(
                xml_with_pre,
                registered,
                force_update,
                origin_date,
                registered_in_core,
            )
            if updated_data:
                response["skip_update"] = True
                response.update(updated_data)
                return response

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
            response.update(registered.data)
            return response

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                item=xml_with_pre.sps_pkg_name,
                action="PidProviderXML.register",
                exception=e,
                exc_traceback=exc_traceback,
                detail=response,
            )
            response.update({"error_msg": str(e), "error_type": str(type(e))})
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
                # garantir que xml_adapter.v3 não tenha conflito
                cls.get_record_by_pid_v3(xml_adapter)
                return xml_pid
            except cls.DoesNotExist:
                return xml_pid
            except PidProviderXMLPidV3ConflictError:
                if not auto_solve_pid_conflict:
                    raise

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
            # obtém os dados de substituição para registrar em other_pid
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
        q = Q()
        if COLLECTION_PREFIX == "scielojournal":
            if xml_adapter.journal_issn_print:
                q |= Q(
                    scielojournal__journal__official__issn_print=xml_adapter.journal_issn_print
                )
            if xml_adapter.journal_issn_electronic:
                q |= Q(
                    scielojournal__journal__official__issn_electronic=xml_adapter.journal_issn_electronic
                )
        else:
            if xml_adapter.journal_issn_print:
                q |= Q(
                    journalproc__journal__official_journal__issn_print=xml_adapter.journal_issn_print
                )
            if xml_adapter.journal_issn_electronic:
                q |= Q(
                    journalproc__journal__official_journal__issn_electronic=xml_adapter.journal_issn_electronic
                )

        for collection in Collection.objects.filter(q):
            registered.collections.add(collection)
        return registered

    @classmethod
    @profile_classmethod
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

        if registered_in_core and not registered.registered_in_core:
            logging.info(
                f"Do not skip update: need to update registered.registered_in_core=True"
            )
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

    @profile_method
    def is_equal_to(self, xml_with_pre):
        return bool(
            self.current_version and self.current_version.is_equal_to(xml_with_pre)
        )

    @classmethod
    @profile_classmethod
    def get_records(cls, xml_adapter):
        qbuilder = QueryBuilderPidProviderXML(xml_adapter)
        q_ids = qbuilder.identifier_queries
        q_journal = qbuilder.issn_query
        q_issue = Q(**qbuilder.issue_params)
        return cls.objects.filter(q_ids | (q_journal & q_issue)).distinct()

    @classmethod
    @profile_classmethod
    def get_record(cls, xml_adapter, records):
        results = records
        if not results.exists():
            raise cls.DoesNotExist
        matched = cls.best_matches(results, xml_adapter)
        if not matched:
            raise cls.DoesNotExist
        return cls.objects.get(id=sorted(matched)[-1][-1])

    @classmethod
    @profile_classmethod
    def get_record_by_pid_v3(cls, xml_adapter):
        # tenta procurar pelo pid_v3
        if not xml_adapter.v3:
            raise ValueError("get_record_by_pid_v3: XML has not pid v3")
        xml_pid_v3 = xml_adapter.v3
        results = (
            cls.objects.filter(Q(v3=xml_pid_v3) | Q(other_pid__pid_in_xml=xml_pid_v3))
        )
        if not results.exists():
            raise cls.DoesNotExist
        matched = cls.best_matches(results, xml_adapter)
        if not matched:
            UnexpectedEvent.create(
                item=xml_adapter.sps_pkg_name,
                action="PidProviderXML.get_record_by_pid_v3",
                exception=PidProviderXMLPidV3ConflictError,
                detail={"xml_adapter": xml_adapter.data, "results": [i.data for i in results]},
            )
            raise PidProviderXMLPidV3ConflictError(
                _("No matching record found for the provided XML data.")
            )
        return cls.objects.get(id=sorted(matched)[-1][-1])

    @profile_method
    def match(self, xml_adapter):
        """
        """
        labels = []
        score = self.title_similarity(xml_adapter) * 100
        if score > 50:
            labels.append("title")
        if score_item := get_score(self.z_surnames, xml_adapter.z_surnames, 10, 100):
            labels.append("z_surnames")
            score += score_item
        if score_item := get_score(self.z_collab, xml_adapter.z_collab, 10, 100):
            labels.append("z_collab")
            score += score_item
        if score_item := get_score(self.z_links, xml_adapter.z_links, 10, 100):
            labels.append("z_links")
            score += score_item
        if score_item := get_score(self.z_partial_body, xml_adapter.z_partial_body, 10, 100):
            labels.append("z_partial_body")
            score += score_item
        return {"score": score, "labels": labels}

    def title_similarity(self, xml_adapter):
        try:
            registered = self.xml_with_pre.article_titles_texts
        except Exception:
            registered = []
        xml_adapter_titles = xml_adapter.xml_with_pre.article_titles_texts
        if xml_adapter_titles == registered:
            return 1
        if not xml_adapter_titles:
            return 0
        if not registered:
            return 0
        words1 = set()
        for item in xml_adapter_titles:
            words1.update(item.split())
        words2 = set()
        for item in registered:
            words2.update(item.split())
        return how_similar(" ".join(sorted(words1)), " ".join(sorted(words2)))

    @classmethod
    def best_matches(cls, results, xml_adapter):
        data = []
        matched = []
        for item in results.iterator():
            response = item.match(xml_adapter)
            score = response["score"]

            if xml_adapter.v2:
                if item.v2 == xml_adapter.v2:
                    score += 100
            elif xml_adapter.order and item.v2 and item.v2.endswith(xml_adapter.order):
                score += 100
            if item.v3 == xml_adapter.v3:
                score += 100
            if item.pkg_name == xml_adapter.pkg_name:
                score += 100
            if item.main_doi == xml_adapter.main_doi:
                score += 100

            _data = response
            _data.update(item.data)
            data.append(_data)

            if score > 50:
                matched.append((score, item.updated.isoformat(), item.id))

        if results.count() > 1 or not matched:
            detail = {
                "xml_adapter_data": xml_adapter.data,
                "data": data,
                "matched": matched,
            } 
            UnexpectedEvent.create(
                item=xml_adapter.sps_pkg_name,
                action="PidProviderXML.best_matches",
                exception=cls.MultipleObjectsReturned,
                detail=detail,
            )
        return matched

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

    @profile_method
    def _add_dates(self, xml_adapter, origin_date, available_since):
        # evita que artigos WIP fique disponíveis antes de estarem públicos
        try:
            self.available_since = available_since or (
                xml_adapter.xml_with_pre.article_publication_date
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
        # registrados passam a ser other pid
        # os pids do XML passam a ser os vigentes
        if not registered_changed:
            return
        for change_args in registered_changed:

            change_args["pid_in_xml"] = change_args.pop("registered")

            change_args["user"] = user
            change_args["pid_provider_xml"] = self

            OtherPid.get_or_create(**change_args)
        self.other_pid_count = self.other_pid.count()
        self.save()

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
            response = {}
            response["input_data"] = xml_with_pre.data
            xml_adapter_data = None
            xml_adapter = xml_sps_adapter.PidProviderXMLAdapter(xml_with_pre)
            xml_adapter_data = xml_adapter.data

            response["xml_adapter_data"] = xml_adapter_data

            try:
                records = cls.get_records(xml_adapter)
                registered = cls.get_record(xml_adapter, records=records)
            except cls.DoesNotExist as exc:
                response.update(
                    {"filename": xml_with_pre.filename, "registered": False}
                )
                return response
            except (cls.MultipleObjectsReturned, exceptions.UnmatchedPidProviderXMLError) as exc:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                response["records"] = [item.data for item in records]
                UnexpectedEvent.create(
                    item=xml_with_pre.sps_pkg_name,
                    action="PidProviderXML.is_registered",
                    exception=exc,
                    exc_traceback=exc_traceback,
                    detail=response,
                )
                response.update({"error_msg": str(exc), "error_type": str(type(exc))})
                return response
            except (
                exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError
            ) as exc:
                raise exc
            except exceptions.RequiredISSNErrorToGetPidProviderXMLError as exc:
                raise exc
            except exceptions.NotEnoughParametersToGetPidProviderXMLError as exc:
                raise exc
            response["registered"] = True
            response.update(registered.data)
            response["is_equal"] = registered.is_equal_to(xml_with_pre)
            return response
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                item=xml_with_pre.sps_pkg_name,
                action="PidProviderXML.is_registered",
                exception=e,
                exc_traceback=exc_traceback,
                detail=response,
            )
            response.update({"error_msg": str(e), "error_type": str(type(e))})
            return response
        return {}

    @classmethod
    @profile_classmethod
    def fix_pid_v2(cls, user, pid_v3, correct_pid_v2):
        try:
            item = cls.objects.get(v3=pid_v3)
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
        for item in cls.objects.filter(
            Q(issn_print__in=issns) | Q(issn_electronic__in=issns),
        ).iterator():
            try:
                invalid = bool(item.xml_with_pre)
            except Exception as e:
                invalid = True

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
            items = cls.objects.filter(pkg_name=pkg_name)
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
                for other_pid in item.other_pid.filter(pid_type="pid_v3"):
                    OtherPid.get_or_create(
                        user=user,
                        pid_type=other_pid.pid_type,
                        pid_in_xml=other_pid.pid_in_xml,
                        version=other_pid.current_version,
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
