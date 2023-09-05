from haystack import indexes

from .models import Article


class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    doi = indexes.MultiValueField(null=True)
    titles = indexes.MultiValueField(null=True)
    la = indexes.MultiValueField(null=True)
    au = indexes.MultiValueField(null=True)
    kw = indexes.MultiValueField(null=True)
    toc_sections = indexes.MultiValueField(null=True)
    ab = indexes.MultiValueField(null=True)
    la_abstract = indexes.MultiValueField(null=True)
    orcid = indexes.MultiValueField(null=True)
    au_orcid = indexes.MultiValueField(null=True)

    journal_title = indexes.CharField(null=True)
    # FIXME 1 artigo pode estar em mais de 1 coleção
    collection = indexes.CharField(null=True)
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

    def prepare_journal_title(self, obj):
        if obj.journal:
            return obj.journal.title

    def prepare_collection(self, obj):
        if obj.journal:
            try:
                # FIXME 1 artigo / journal pode estar em mais de 1 coleção
                return obj.journal.collection.main_name
            except AttributeError:
                pass

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

    def prepare_toc_sections(self, obj):
        if obj.toc_sections:
            return [toc_section.plain_text for toc_section in obj.toc_sections.all()]

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
            return obj.journal.collection.domain
        except AttributeError:
            pass

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
    submitter = indexes.CharField(model_attr="creator", index_fieldname="item.submitter", null=True)
    deleted = indexes.CharField(index_fieldname="item.deleted", null=True)
    public = indexes.CharField(index_fieldname="item.public", null=True)
    collections = indexes.MultiValueField(index_fieldname="item.collections", null=True)
    publishers = indexes.MultiValueField(index_fieldname="item.communities", null=True)
    titles = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.title")
    creator = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.creator")
    kw = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.subject")
    description = indexes.MultiValueField(index_fieldname="metadata.dc.description")
    dates = indexes.MultiValueField(index_fieldname="metadata.dc.date")
    type = indexes.CharField(model_attr="article_type", index_fieldname="metadata.dc.type", null=True)
    identifier = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.identifier")
    la = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.language")
    license = indexes.MultiValueField(index_fieldname="metadata.dc.rights")
    sources = indexes.MultiValueField(index_fieldname="metadata.dc.source")
    compile = indexes.CharField(null=True, index_fieldname="item.compile", use_template=True)

    def prepare_doi(self, obj):
        if obj.doi:
            return "".join([doi.value for doi in obj.doi.all()])

    def prepare_updated(self, obj):
        """
        2022-12-20T15:18:22Z
        """
        return obj.updated.strftime('%Y-%m-%dT%H:%M:%SZ')

    def prepare_deleted(self, obj):
        return False
    
    def prepare_public(self, obj):
        return True
    
    def prepare_collections(self, obj):
        return ["SciELO",]
    
    def prepare_publishers(self, obj):
        if not obj.publisher: 
            return [" ",]
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
        return [" ",]
        
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
        return [" ",]

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
