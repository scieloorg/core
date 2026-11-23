from core.utils.profiling_tools import profile_method, profile_staticmethod
from pid_provider.base_pid_provider import BasePidProvider
from pid_provider.models import PidProviderXML


class PidProvider(BasePidProvider):
    """
    Recebe XML para validar ou atribuir o ID do tipo v3
    """

    @staticmethod
    @profile_staticmethod
    def get_xmltree(pid_v3, collection_acron=None):
        """
        XML da coleção (collection_acron) ou, sem coleção, o de
        PidProviderXML.current_version (ver PidProviderXML.get_xml_with_pre)
        """
        try:
            return PidProviderXML.get_xml_with_pre(
                pid_v3, collection_acron=collection_acron
            ).xmltree
        except (PidProviderXML.DoesNotExist, AttributeError):
            return None

    @staticmethod
    @profile_staticmethod
    def get_sps_pkg_name(pid_v3, collection_acron=None):
        """
        Nome do pacote do XML da coleção (collection_acron) ou, sem coleção,
        o de PidProviderXML.current_version (ver
        PidProviderXML.get_xml_with_pre)
        """
        try:
            return PidProviderXML.get_xml_with_pre(
                pid_v3, collection_acron=collection_acron
            ).sps_pkg_name
        except (PidProviderXML.DoesNotExist, AttributeError):
            return None

    # OBSOLETO: o pid v2 é corrigido por coleção em proc.models.ArticleProc.fix_pid_v2
    @profile_method
    def fix_pid_v2(self, user, pid_v3, correct_pid_v2):
        return PidProviderXML.fix_pid_v2(user, pid_v3, correct_pid_v2)
