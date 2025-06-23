from collections import defaultdict
from functools import lru_cache

from core.utils.articlemeta_dict_utils import add_items, add_to_result
from journal.models import SciELOJournal, TitleInDatabase


class ArticlemetaJournalFormatter:
    """Formatador para dados do ArticleMeta"""
    
    def __init__(self, obj):
        self.obj = obj
        self.result = defaultdict(list)
        self._scielo_journal = None
        self._publisher_history = None
        self._medline_titles = None
    
    @property
    def scielo_journal(self):
        if self._scielo_journal is None:
            self._scielo_journal = SciELOJournal.objects.select_related(
                'collection', 'journal'
            ).filter(
                journal=self.obj, 
                collection__is_active=True
            ).first()
        return self._scielo_journal
    
    @property
    def publisher_history(self):
        if self._publisher_history is None:
            self._publisher_history = self.obj.publisher_history.select_related(
                'institution__institution', 'institution__institution__location'
            ).all()
        return self._publisher_history
    
    @property
    @lru_cache(maxsize=1)
    def medline_titles(self):
        return list(TitleInDatabase.objects.filter(
            journal=self.obj, 
            indexed_at__acronym__iexact="medline"
        ))
    
    def format(self):
        """Formata todos os dados do journal"""
        formatters = [
            self._format_basic_info,
            self._format_publication_info,
            self._format_publisher_info,
            self._format_indexing_info,
            self._format_metadata
        ]
        
        for formatter in formatters:
            formatter()
        
        return dict(self.result)
    
    def _format_basic_info(self):
        """Informações básicas do journal"""
        add_to_result("collection", self.scielo_journal.collection.acron3 if self.scielo_journal.collection else None, self.result)
        add_to_result("code", self.scielo_journal.issn_scielo if self.scielo_journal else None, self.result)
        add_to_result("v5", self.obj.type_of_literature, self.result)
        add_to_result("v6", self.obj.treatment_level, self.result)
        add_to_result("v10", self.obj.center_code, self.result)
        add_to_result("v20", self.obj.national_code, self.result)
        add_to_result("v30", self.obj.identification_number, self.result)
    
    def _format_publication_info(self):
        """Informações de publicação"""
        if self.obj.official:
            official = self.obj.official
            add_to_result("v100", official.title, self.result)
            add_to_result("v301", official.initial_year, self.result)
            add_to_result("v302", official.initial_volume, self.result)
            add_to_result("v303", official.initial_number, self.result)
            
            # Título paralelo
            if hasattr(official, 'parallel_titles'):
                add_items("v230", [pt.text for pt in official.parallel_titles if pt.text], self.result)
    
    def _format_publisher_info(self):
        """Informações do publisher"""
        publishers = list(self.publisher_history)
        
        add_items("v310", [p.get_institution_country_name for p in publishers], self.result)
        add_items("v320", [p.get_instition_state_acronym for p in publishers], self.result)
        add_items("v480", [p.get_institution_name for p in publishers], self.result)
        add_items("v490", [p.get_institution_city_name for p in publishers], self.result)
    
    def _format_indexing_info(self):
        """Informações de indexação"""
        # Medline
        medline_data = self.medline_titles
        add_items("v420", [m.identifier for m in medline_data], self.result)
        add_items("v421", [m.title for m in medline_data], self.result)
        
        # Indexed at
        add_items("v450", [idx.name for idx in self.obj.indexed_at.all()], self.result)
    
    def _format_metadata(self):
        """Metadados diversos"""
        add_to_result("v940", self.obj.created.isoformat(), self.result)
        add_to_result("v941", self.obj.updated.isoformat(), self.result)


def get_articlemeta_format_title(obj):
    formatter = ArticlemetaJournalFormatter(obj)
    return formatter.format()