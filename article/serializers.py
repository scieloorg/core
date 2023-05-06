from rest_framework import serializers

from article.models import Article


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = (
            # "xml_uri",
            # "pid_v3",
            "pid_v2",
            # "aop_pid",
        )
