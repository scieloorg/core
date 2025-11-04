from haystack import indexes
from legendarium.formatter import descriptive_format

from journal.models import SciELOJournal

from .models import Article


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
    orcid = indexes.MultiValueField(null=True)
    au_orcid = indexes.MultiValueField(null=True)
    collab = indexes.MultiValueField(null=True)

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
    subject_areas = indexes.MultiValueField(null=True)
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
            if title.language:
                data[f"ti_{title.language.code2}"] = title.plain_text
            else:
                data["ti_"] = title.plain_text

        # prepare abstracts
        for ab in obj.abstracts.all():
            if ab.language:
                data[f"ab_{ab.language.code2}"] = ab.plain_text
            else:
                data["ab_"] = ab.plain_text

        if obj.journal:
            collections = obj.collections
            # prepara the fulltext_pdf_*
            # FIXME
            # Article languages nao tem a mesma correpondencia de languages PDF
            for collection in collections:
                for lang in obj.languages.all():
                    data["fulltext_pdf_%s" % (lang.code2)] = (
                        "http://%s/scielo.php?script=sci_pdf&pid=%s&tlng=%s"
                        % (
                            collection.domain,
                            obj.pid_v2,
                            lang.code2,
                        )
                    )

            # prepara the fulltext_html_*
            # FIXME
            # Article languages nao tem a mesma correpondencia de languages HTML
            for collection in collections:
                for lang in obj.languages.all():
                    data["fulltext_html_%s" % (lang.code2)] = (
                        "http://%s/scielo.php?script=sci_arttext&pid=%s&tlng=%s"
                        % (
                            collection.domain,
                            obj.pid_v2,
                            lang.code2,
                        )
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
        collections = obj.collections
        urls = []

        if obj.journal:
            for collection in collections:
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
            sci_journals = SciELOJournal.objects.filter(
                journal=obj.journal, collection__is_active=True
            )
            return [sci_journal.journal_acron for sci_journal in sci_journals]

    def prepare_year_cluster(self, obj):
        return str(obj.pub_date_year)

    def prepare_collection(self, obj):
        collections = obj.collections
        return (
            [collection.acron3 for collection in collections] if obj.journal else None
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

    def prepare_collab(self, obj):
        if obj.collab:
            return [collab.institution_author for collab in obj.collab.all()]

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

    def prepare_domain(self, obj):
        collections = obj.collections
        try:
            return collections.all()[0].domain
        except AttributeError:
            pass

    def prepare_pg(self, obj):
        return "%s-%s" % (obj.first_page, obj.last_page)

    def prepare_wok_citation_index(self, obj):
        return [wos.code for wos in obj.journal.wos_db.all()] if obj.journal else None

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_classic_public=True)


class ArticleOAIIndex(indexes.SearchIndex, indexes.Indexable):
    """
    The format of the data:

        "item.id":1,
        "item.handle":"54v7n5FBfdfC3KYFbbGWZYP",
        "item.id":"54v7n5FBfdfC3KYFbbGWZYP",
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
    id = indexes.CharField(index_fieldname="item.handle", null=True)
    item_id = indexes.CharField(index_fieldname="item.id", null=True)
    updated = indexes.CharField(index_fieldname="item.lastmodified", null=True)
    submitter = indexes.CharField(
        model_attr="creator", index_fieldname="item.submitter", null=True
    )
    deleted = indexes.CharField(index_fieldname="item.deleted", null=True)
    public = indexes.CharField(index_fieldname="item.public", null=True)
    collections = indexes.MultiValueField(index_fieldname="item.collections", null=True)
    communities = indexes.MultiValueField(index_fieldname="item.communities", null=True)
    titles = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.title")
    creator = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.creator")
    collab = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.collab")
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

    def prepare_id(self, obj):
        """This field is the identifier of the record
        The OAI persistent identifier prefix for SciELO is ``oai:scielo:``
        We are giving preference to pid_v2 then pid-v3 and finally DOI
        """
        return "oai:scielo:%s" % obj.pid_v2 or obj.doi or obj.pid_v3

    def prepare_item_id(self, obj):
        """This field is the identifier of the record
        The OAI persistent identifier prefix for SciELO is ``oai:scielo:``
        We are giving preference to pid_v2 then pid-v3 and finally DOI
        """
        return "oai:scielo:%s" % obj.pid_v2 or obj.doi or obj.pid_v3

    def prepare_updated(self, obj):
        """
        This is the lastmodified to the OAI-PMH protocol.
        The format of the date must be something like: 2024-03-06 15:48:25.
        The strftime: 2022-12-20T15:18:22Z
        The param ``from`` and ``until`` considers this field as filtering.
        """
        return obj.updated.strftime("%Y-%m-%dT%H:%M:%SZ")

    def prepare_deleted(self, obj):
        """This is a soft delete on the index, so in the application which handle
        the data must flag as deleted to the index, by now we are set as ``False``
        """
        return False

    def prepare_public(self, obj):
        """Until now we dont have a field on data set as public,
        by now we are set as ``False``
        """
        return True

    def prepare_collections(self, obj):
        """The ISSN is on SciELO Journal models.SciELOJournal.objects.filter(journal=j)[0].issn_scielo"""
        # set com os issns
        if obj.journal:
            return set(
                [
                    j.issn_scielo
                    for j in SciELOJournal.objects.filter(journal=obj.journal)
                ]
            )

    def prepare_communities(self, obj):
        """The collection field is multi-value, so may contain N collection.
        IMPORTANT: the attribute of the ``obj`` is a property with a query which
        can return no record that is very weak.
        """
        if obj.collections:
            if obj.collections:
                return ["com_%s" % col for col in obj.collections]

    def prepare_titles(self, obj):
        """The list of titles."""
        if obj.titles:
            return set([title.plain_text for title in obj.titles.all()])

    def prepare_creator(self, obj):
        """The list of authors is the researchers on the models that related with
        class PersonName, so we used ``select_related`` to ensure that
        person_name is not null.
        """
        if obj.researchers:
            researchers = obj.researchers.select_related("person_name").filter(
                person_name__isnull=False
            )
            return set([str(researcher.person_name) for researcher in researchers])

    def prepare_collab(self, obj):
        """This is the instituional author."""
        if obj.collab:
            return set([collab.collab for collab in obj.collab.all()])

    def prepare_kw(self, obj):
        """The keywords of the article."""
        if obj.keywords:
            return set([keyword.text for keyword in obj.keywords.all()])

    def prepare_description(self, obj):
        """The abstracts of the articles
        This is a property that filter by article ``DocumentAbstract.objects.filter(article=self)``
        """
        if obj.abstracts:
            return set([abs.plain_text for abs in obj.abstracts.all()])

    def prepare_dates(self, obj):
        """This the publication date, that is format by YYYY-MM-DD
        In the model this field is seperated into pub_date_day, pub_date_month and pub_date_year
        """
        return [
            "-".join(
                [
                    obj.pub_date_year or "",
                    obj.pub_date_month or "",
                    obj.pub_date_day or "",
                ]
            ),
        ]

    def prepare_la(self, obj):
        """The language of the article."""
        if obj.languages:
            return set([language.code2 for language in obj.languages.all()])

    def prepare_identifier(self, obj):
        """Add the all identifier to the article:
        PID v2
        PID v3
        DOI
        URL old format:
            Example: https://www.scielo.br/scielo.php?script=sci_arttext&pid=S0102-311X2019000104001&lang=pt
        """
        idents = set()

        if obj.journal:
            collections = obj.collections
            for collection in collections:
                for lang in obj.languages.all():
                    idents.add(
                        "http://%s/scielo.php?script=sci_arttext&pid=%s&tlng=%s"
                        % (
                            collection.domain,
                            obj.pid_v2,
                            lang.code2,
                        )
                    )

        if obj.doi:
            idents.update([doi.value for doi in obj.doi.all()])

        if obj.pid_v2:
            idents.add(obj.pid_v2)

        if obj.pid_v3:
            idents.add(obj.pid_v3)

        return idents

    def prepare_license(self, obj):
        if obj.license and obj.license.license_type:
            return [obj.license.license_type]

    def prepare_sources(self, obj):
        # property no article.
        # Acta Cirúrgica Brasileira, Volume: 37, Issue: 7, Article number: e370704, Published: 10 OCT 2022
        try:
            return obj.source
        except Exception as ex:
            return ""

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_classic_public=True)

