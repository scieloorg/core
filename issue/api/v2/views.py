from issue.api.v1.views import IssueViewSet as IssueViewSetV1

from .serializers import IssueSerializer


class IssueViewSet(IssueViewSetV1):
    """
    Decisão: reutiliza filtros e o formato ?formats=articlemeta da v1;
    muda apenas o serializer padrão (ver issue.api.v2.serializers).
    """

    serializer_class = IssueSerializer

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        if serializer_class is IssueViewSetV1.serializer_class:
            return IssueSerializer
        return serializer_class
