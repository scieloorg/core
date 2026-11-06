from rest_framework import serializers

from issue.api.v1.serializers import IssueSerializer as IssueSerializerV1


class IssueSerializer(IssueSerializerV1):
    """
    Serializer de Issue da API v2.

    Decisões em relação à v1:
    - issue_pid é adicionado: pid já estabelecido do fascículo (issn_scielo +
      ano + ordem) na coleção informada em ?collection=, obtido via AMIssue;
      pode divergir entre coleções
    - issue_pid_suffix é mantido: ordem calculada por volume/número/suplemento,
      usada para criar pids novos (ex.: pid v2 de artigos novos no scms-upload);
      não corresponde necessariamente ao issue_pid
    - legacy_issue (herdado da v1) traz sempre todas as chaves legadas, de todas
      as coleções, independente de ?collection=
    """

    issue_pid = serializers.SerializerMethodField()

    class Meta(IssueSerializerV1.Meta):
        fields = IssueSerializerV1.Meta.fields + ["issue_pid"]

    def get_issue_pid(self, obj):
        # Decisões:
        # - com ?collection=: issue_pid da coleção correspondente
        # - sem ?collection=: None, pois não há um issue_pid único entre
        #   coleções; os pids de todas as coleções estão em legacy_issue
        # - create=False: requisição GET não deve gravar no banco
        request = self.context.get("request")
        collection_acron3 = request and request.query_params.get("collection")
        if not collection_acron3:
            return None
        return obj.get_issue_pid(collection_acron3, create=False)
