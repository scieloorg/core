from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from article import models

from .serializers import ArticleSerializer
from core.validators import validate_params
from core.utils.utils import params_api

class ArticlePagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size' 
    max_page_size = 1000


class ArticleViewSetGeneric(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    http_method_names = ["get"]
    queryset = models.Article.objects.all()


class ArticleViewSet(ArticleViewSetGeneric):
    pagination_class = ArticlePagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # # fazer fora da funcao params_api
        # # issn = self.request.query_params.get("issn")
        # # pub_date_year=year,
        doi_prefix = self.request.query_params.get('doi_prefix', None)
        issn_print = self.request.query_params.get("issn_print")
        issn_electronic = self.request.query_params.get("issn_electronic")
        year = self.request.query_params.get("year")
        thematic_areas = self.request.query_params.get("thematic_areas")
        toc_sections = self.request.query_params.get("toc_sections")
        article_type = self.request.query_params.get("article_type")
        pid_v3 = self.request.query_params.get("pid_v3")
        pid_v2 = self.request.query_params.get("pid_v2")
        license = self.request.query_params.get("license")
        acron3_collection = self.request.query_params.get("collection")
        affiliation_code = self.request.query_params.get("affiliation_code")
        from_date_created = self.request.query_params.get("from_date_created")
        until_date_created = self.request.query_params.get("until_date_created")
        from_date_updated = self.request.query_params.get("from_date_updated")
        until_date_updated = self.request.query_params.get("until_date_updated")

        validate_params(
            self.request,
            "doi_prefix",
            "issn_print",
            "issn_electronic",
            "year",
            "thematic_areas",
            "toc_sections",
            "article_type",
            "pid_v3",
            "pid_v2",
            "license",
            "acron3_collection",
            "affiliation_code",
            "from_date_created",
            "until_date_created",
            "from_date_updated",
            "until_date_updated",
            "page",
            ""
        )


        params = {}
        params = params_api(
            journal__officialjournal__issn_print=issn_print,
            journal__officialjournal__issn_electronic=issn_electronic,
            issue__year=year,
            doi__value__startswith=doi_prefix,
            journal__subject__value__insubject__value__in=thematic_areas.split(",") if thematic_areas else None,
            toc_sections__plain_text=toc_sections,
            article_type=article_type,
            pid_v3=pid_v3,
            pid_v2=pid_v2,
            publisher__institution__location__country__acronym=affiliation_code,
            article_license__icontains="".join(("/", license, "/")) if license else None,
            journal__scielojournal__collection__acron3=acron3_collection,
            created__gte=from_date_created.replace("/", "-") if from_date_created else None,
            created__lte=until_date_created.replace("/", "-") if until_date_created else None,
            updated__gte=from_date_updated.replace("/", "-") if from_date_updated else None,
            updated__lte=until_date_updated.replace("/", "-") if until_date_updated else None            
        )

        return queryset.filter(**params)
    

    # def list(self, request, *args, **kwargs):
    #     query_params = request.query_params

    #     
    #     queryset = self.filter_queryset(self.get_queryset())
    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)

    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response({
    #         'parameters_used': query_params,
    #         'results': serializer.data,
    #     })