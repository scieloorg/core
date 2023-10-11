from haystack import indexes

from .models import Article
from journal.models import SciELOJournal


class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    # doi
    doi = indexes.MultiValueField(null=True)

    # ids
    ids = indexes.MultiValueField(null=True)

    # URLs
    ur = indexes.MultiValueField(null=True)

    titles = indexes.MultiValueField(index_fieldname="ti", null=True)
    la = indexes.MultiValueField(null=True)
    au = indexes.MultiValueField(null=True)
    kw = indexes.MultiValueField(null=True)
    # toc_sections = indexes.MultiValueField(null=True)
    ab = indexes.MultiValueField(null=True)
    la_abstract = indexes.MultiValueField(null=True)
    orcid = indexes.MultiValueField(null=True)
    au_orcid = indexes.MultiValueField(null=True)

    collection = indexes.MultiValueField(index_fieldname="in", null=True)
    journal_title = indexes.CharField(null=True)
    type = indexes.CharField(model_attr="article_type", null=True)
    pid = indexes.CharField(model_attr="pid_v2", null=True)
    pid_v3 = indexes.CharField(model_attr="pid_v3", null=True)
    publication_year = indexes.CharField(model_attr="pub_date_year", null=True)
    domain = indexes.CharField(null=True)
    issue = indexes.CharField(null=True)
    volume = indexes.CharField(null=True)
    elocation = indexes.CharField(model_attr="elocation_id", null=True)
    start_page = indexes.CharField(model_attr="first_page", null=True)
    end_page = indexes.CharField(model_attr="last_page", null=True)
    pg = indexes.CharField(null=True)
    wok_citation_index = indexes.CharField(null=True)
    subject_areas = indexes.CharField(null=True)
    ta_cluster = indexes.CharField(null=True)
    year_cluster = indexes.CharField(null=True)

    def prepare(self, obj):
        """ "
        Here add the title to with dynamic fields.

        Example ti_* (title and the translations)

        About the prepare function see: https://django-haystack.readthedocs.io/_/downloads/en/master/pdf/
        """
        data = super().prepare(obj)

        # prepare the titles ti_*
        for title in obj.titles.all():
            data["ti_%s" % title.language.code2] = title.plain_text

        if obj.journal:
            # prepara the fulltext_pdf_*
            for collection in obj.journal.collection.all():
                for lang in obj.languages.all():
                    data[
                        "fulltext_pdf_%s" % (lang.code2)
                    ] = "http://%s/scielo.php?script=sci_pdf&pid=%s&tlng=%s" % (
                        collection.domain,
                        obj.pid_v2,
                        lang.code2,
                    )

            # prepara the fulltext_html_*
            for collection in obj.journal.collection.all():
                for lang in obj.languages.all():
                    data[
                        "fulltext_html_%s" % (lang.code2)
                    ] = "http://%s/scielo.php?script=sci_arttext&pid=%s&tlng=%s" % (
                        collection.domain,
                        obj.pid_v2,
                        lang.code2,
                    )

        return data

    def prepare_ids(self, obj):
        """
        This field have all ids for the article.

        Example:
        """
        ids = []

        if obj.pid_v2:
            ids.append(obj.pid_v2)

        if obj.pid_v3:
            ids.append(obj.pid_v3)

        if obj.id:
            ids.append(obj.id)

        return ids

    def prepare_ur(self, obj):
        """
        This field is a URLs for all collection of this article.
        """
        urls = []

        if obj.journal:
            for collection in obj.journal.collection.all():
                urls.append(
                    "http://%s/scielo.php?script=sci_arttext&pid=%s"
                    % (collection.domain, obj.pid_v2)
                )

        return urls

    def prepare_journal_title(self, obj):
        if obj.journal:
            return obj.journal.title

    def prepare_subject_areas(self, obj):
        return (
            [subj_areas.value for subj_areas in obj.journal.subject.all()]
            if obj.journal
            else None
        )

    def prepare_ta_cluster(self, obj):
        """
        This function get the SciELOJournal.journal_acron to get the acronym to the journal.
        """
        if obj.journal:
            sci_journal = SciELOJournal.objects.get(journal=obj.journal)
            return sci_journal.journal_acron

    def prepare_year_cluster(self, obj):
        """
        This function get the SciELOJournal.journal_acron to get the acronym to the journal.
        """
        return str(obj.pub_date_year)

    def prepare_collection(self, obj):
        return (
            [collection.acron3 for collection in obj.journal.collection.all()]
            if obj.journal
            else None
        )

    def prepare_doi(self, obj):
        if obj.doi:
            return [doi.value for doi in obj.doi.all()]

    def prepare_la(self, obj):
        if obj.languages:
            return [language.code2 for language in obj.languages.all()]

    def prepare_titles(self, obj):
        if obj.titles:
            return [title.plain_text for title in obj.titles.all()]

    def prepare_orcid(self, obj):
        if obj.researchers:
            return [research.orcid for research in obj.researchers.all()]

    def prepare_au_orcid(self, obj):
        if obj.researchers:
            return [f"{research.orcid}" for research in obj.researchers.all()]

    def prepare_au(self, obj):
        if obj.researchers:
            return [research.get_full_name for research in obj.researchers.all()]

    def prepare_kw(self, obj):
        if obj.keywords:
            return [keyword.text for keyword in obj.keywords.all()]

    # def prepare_toc_sections(self, obj):
    #     if obj.toc_sections:
    #         return [toc_section.plain_text for toc_section in obj.toc_sections.all()]

    def prepare_issue(self, obj):
        try:
            return obj.issue.number
        except AttributeError:
            pass

    def prepare_volume(self, obj):
        try:
            return obj.issue.volume
        except AttributeError:
            pass

    def prepare_ab(self, obj):
        if obj.abstracts:
            return [abstract.plain_text for abstract in obj.abstracts.all()]

    def prepare_la_abstract(self, obj):
        if obj.abstracts:
            return [abstract.language for abstract in obj.abstracts.all()]

    def prepare_domain(self, obj):
        try:
            return obj.journal.collection.all()[0].domain
        except AttributeError:
            pass

    def prepare_pg(self, obj):
        return "%s-%s" % (obj.first_page, obj.last_page)

    def prepare_wok_citation_index(self, obj):
        return [wos.code for wos in obj.journal.wos_db.all()] if obj.journal else None

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.all()


class ArticleOAIIndex(indexes.SearchIndex, indexes.Indexable):
    """
    The format of the data:

        "item.id":1,
        "item.handle":"oai:redi.anii.org.uy:20.500.12381/2671",
        "item.lastmodified":"2022-12-20T15:18:22Z",
        "item.submitter":"submitter",
        "item.deleted":false,
        "item.public":true,
        "item.collections":["TEST"],
        "item.communities":["com_INST01"],
        "metadata.dc.title":["Descripción de estados fenológicos de pecán."],
        "metadata.dc.creator":["PROGRAMA NACIONAL PRODUCCIÓN FRUTÍCOLA"],
        "metadata.dc.subject":["NUEZ",
          "FRUTALES",
          "PECAN",
          "FENOLOGIA"],
        "metadata.dc.description":[""],
        "metadata.dc.date":["2022-12-16T20:50:16Z",
          "2022-12-16T20:50:16Z",
          "2016",
          "2022-12-16T20:50:16Z"],
        "metadata.dc.type":["info:eu-repo/semantics/publishedVersion",
          "info:eu-repo/semantics/report"],
        "metadata.dc.identifier":["http://www.ainfo.inia.uy/consulta/busca?b=pc&id=56088&biblioteca=vazio&busca=56088&qFacets=56088"],
        "metadata.dc.language":["es",
          "spa"],
        "metadata.dc.rights":["info:eu-repo/semantics/openAccess",
          "Acceso abierto"],
        "metadata.dc.source":["reponame:Ainfo",
          "instname:Instituto Nacional de Investigación Agropecuaria",
          "instacron:Instituto Nacional de Investigación Agropecuaria"],
        "item.compile":"<metadata xmlns=\"http://www.lyncode.com/xoai\"\n"

    """

    text = indexes.CharField(document=True, use_template=True)
    id = indexes.CharField(model_attr="id", index_fieldname="item.handle", null=True)
    item_id = indexes.CharField(model_attr="id", index_fieldname="item.id", null=True)
    updated = indexes.CharField(index_fieldname="item.lastmodified", null=True)
    submitter = indexes.CharField(
        model_attr="creator", index_fieldname="item.submitter", null=True
    )
    deleted = indexes.CharField(index_fieldname="item.deleted", null=True)
    public = indexes.CharField(index_fieldname="item.public", null=True)
    collections = indexes.MultiValueField(index_fieldname="item.collections", null=True)
    publishers = indexes.MultiValueField(index_fieldname="item.communities", null=True)
    titles = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.title")
    creator = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.creator")
    kw = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.subject")
    description = indexes.MultiValueField(index_fieldname="metadata.dc.description")
    dates = indexes.MultiValueField(index_fieldname="metadata.dc.date")
    type = indexes.CharField(
        model_attr="article_type", index_fieldname="metadata.dc.type", null=True
    )
    identifier = indexes.MultiValueField(
        null=True, index_fieldname="metadata.dc.identifier"
    )
    la = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.language")
    license = indexes.MultiValueField(index_fieldname="metadata.dc.rights")
    sources = indexes.MultiValueField(index_fieldname="metadata.dc.source")
    compile = indexes.CharField(
        null=True, index_fieldname="item.compile", use_template=True
    )

    def prepare_doi(self, obj):
        if obj.doi:
            return "".join([doi.value for doi in obj.doi.all()])

    def prepare_updated(self, obj):
        """
        2022-12-20T15:18:22Z
        """
        return obj.updated.strftime("%Y-%m-%dT%H:%M:%SZ")

    def prepare_deleted(self, obj):
        return False

    def prepare_public(self, obj):
        return True

    def prepare_collections(self, obj):
        return [
            "SciELO",
        ]

    def prepare_publishers(self, obj):
        if not obj.publisher:
            return [
                " ",
            ]
        return [obj.publisher]

    def prepare_titles(self, obj):
        if obj.titles:
            return [title.plain_text for title in obj.titles.all()]

    def prepare_creator(self, obj):
        if obj.researchers:
            return [researcher for researcher in obj.researchers.all()]

    def prepare_kw(self, obj):
        if obj.keywords:
            return [keyword.text for keyword in obj.keywords.all()]

    def prepare_description(self, obj):
        if obj.abstracts:
            return [abs.plain_text for abs in obj.abstracts.all()]

    def prepare_dates(self, obj):
        return [
            " ",
        ]

    def prepare_la(self, obj):
        if obj.languages:
            return [language.code2 for language in obj.languages.all()]

    def prepare_identifier(self, obj):
        if obj.doi:
            dois = [doi.value for doi in obj.doi.all()]
        return dois + [obj.pid_v2, obj.pid_v3]

    def prepare_license(self, obj):
        if obj.license:
            return [license.license_type for license in obj.license.all()]

    def prepare_sources(self, obj):
        return [
            " ",
        ]

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
