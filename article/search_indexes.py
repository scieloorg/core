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
    collection = indexes.CharField(null=True)
    type = indexes.CharField(model_attr="article_type", null=True)
    pid = indexes.CharField(model_attr="pid_v2", null=True)
    pid_v3 = indexes.CharField(model_attr="pid_v3", null=True)
    publication_year = indexes.CharField(model_attr="pub_date_year", null=True)
    domain = indexes.CharField(null=True)
    issue = indexes.CharField(null=True)
    volume = indexes.CharField(null=True)
    elocation = indexes.CharField(null=True)
    start_page = indexes.CharField(model_attr="first_page", null=True)
    end_page = indexes.CharField(model_attr="last_page", null=True)

    def prepare_journal_title(self, obj):
        if obj.journal:
            return obj.journal.title 

    def prepare_collection(self, obj):
        if obj.journal:
            try:
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
        if obj.issue:
            try:
                return obj.issue.number
            except AttributeError:
                pass

    def prepare_volume(self, obj):
        if obj.issue:
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
        if obj.journal:
            try:
                return obj.journal.collection.domain
            except AttributeError:
                pass

    def get_model(self):
        return Article
    
    def index_queryset(self, using=None):
        return self.get_model().objects.all()