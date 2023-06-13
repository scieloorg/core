from haystack import indexes
from .models import Article

class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    doi = indexes.MultiValueField(null=True)
    titles = indexes.MultiValueField(null=True)
    # languages = indexes.MultiValueField(null=True)
    researchers = indexes.MultiValueField(null=True)
    keywords = indexes.MultiValueField(null=True)
    toc_sections = indexes.MultiValueField(null=True)

    journal = indexes.CharField(null=True)
    article_type = indexes.CharField(model_attr="article_type", null=True)
    pid_v2 = indexes.CharField(model_attr="pid_v2", null=True)
    pid_v3 = indexes.CharField(model_attr="pid_v3", null=True)
    pub_date_year = indexes.CharField(model_attr="pub_date_year", null=True)
    
    
    def prepare_journal(self, obj):
        if obj.journal:
            return obj.journal.title 

    def prepare_doi(self, obj):
        if obj.doi:
            return [doi.value for doi in obj.doi.all()] 
        
    def prepare_titles(self, obj):
        if obj.titles:
            return [title.plain_text for title in obj.titles.all()]
        
    # def prepare_languages(self, obj):
    #     if obj.languages:
    #         return [language.code2 for language in obj.languages.all()]

    def prepare_researchers(self, obj):
        if obj.researchers:
            return [research.get_full_name for research in obj.researchers.all()]
        
    def prepare_keywords(self, obj):
        if obj.keywords:
            return [keyword.text for keyword in obj.keywords.all()]
        
    def prepare_toc_sections(self, obj):
        if obj.toc_sections:
            return [toc_section.plain_text for toc_section in obj.toc_sections.all()]
        
    def get_model(self):
        return Article
    
    def index_queryset(self, using=None):
        return self.get_model().objects.all()