from collections import defaultdict
from functools import lru_cache

from core.utils.articlemeta_dict_utils import add_items, add_to_result
from journal.models import SciELOJournal, TitleInDatabase
from article.models import Article


class ArticlemetaIssueFormatter:
    """Formatador para dados do Issue"""
    def __init__(self, obj):
        self.obj = obj
        self.result = defaultdict(list)
        self._scielo_journal = None
        self._medline_titles = None
    
    @property
    def scielo_journal(self):
        if self._scielo_journal is None:
            self._scielo_journal = SciELOJournal.objects.select_related(
                'journal'
            ).filter(
                journal=self.obj.journal,
            ).first()
        return self._scielo_journal

    @property
    @lru_cache(maxsize=1)
    def medline_titles(self):
        return list(TitleInDatabase.objects.filter(
            journal=self.obj.journal, 
            indexed_at__acronym__iexact="medline"
        ))
    
    def format(self):
        """Formata todos os dados do issue"""
        formatters = [
            self._format_basic_info,
            self._format_publication_info,
            self._format_journal_info,
            self._format_metadata,
            self._format_system_info,
            self._format_legend_bibliographic,
            self._format_supplement_info,
            self._format_title_summary,
            self._format_institution_info,
            self._format_field_use_system,
            self._format_register_order_info,
            self._format_title_in_database
        ]
        
        for formatter in formatters:
            formatter()
        
        return dict(self.result)

    def _format_basic_info(self):
        """Informações básicas do issue"""
        # Path to base issue
        add_to_result("v4", f"v{self.obj.volume}n{self.obj.number}", self.result)
        
        # Dado legado pouco utilizado
        # "v6": Ordem de publicação dos fascículos para apresentação na interface
        
        # Volume e número
        add_to_result("v31", self.obj.volume, self.result)
        add_to_result("v32", self.obj.number, self.result)
        
        # Title of issue
        add_to_result("v36", f"{self.obj.year}{self.obj.number}", self.result)
        
        # Issue titles
        if hasattr(self.obj, 'issue_title'):
            add_items("v33", [title for title in self.obj.issue_title.all()], self.result)
        
        # Part (dado fixo)
        self.result["v34"].append({"_": None})
        
        # Status issue (fixo)
        add_to_result("v42", '1', self.result)

    def _format_publication_info(self):
        """Informações de publicação"""
        year = self.obj.year
        month = self.obj.month
        
        if year and month:
            self.result["v64"].append({"a": year, "m": month})
            add_to_result("v65", year + month + '00', self.result)
        elif year:
            self.result["v64"].append({"a": year})
            add_to_result("v65", year + '0000', self.result)
            
    def _format_journal_info(self):
        """Informações do journal"""
        journal = self.obj.journal

        add_to_result("v30", journal.short_title, self.result)
        add_to_result("v130", journal.title if journal.title else None, self.result)
        add_to_result("v117", journal.standard.code if journal.standard else None, self.result)

        if self.scielo_journal:
            add_to_result("v35", self.scielo_journal.issn_scielo, self.result)
            add_to_result("v930", self.scielo_journal.journal_acron, self.result)
        
        if journal.vocabulary:
            add_to_result("v85", journal.vocabulary.acronym, self.result)

        if journal.official and journal.official.iso_short_title:
            add_to_result("v151", journal.official.iso_short_title, self.result)

        if journal.official and hasattr(journal.official, 'parallel_titles'):
            add_items("v230", [pt.text for pt in journal.official.parallel_titles if pt.text], self.result)

    def _format_institution_info(self):
        """Informações de instituições"""
        journal = self.obj.journal
        history = {
            "v62": "copyright_holder_history",
            "v140": "sponsor_history",
            "v480": "publisher_history"
        }

        for key, attr in history.items():
            history = getattr(journal, attr, None)
            if history:
                items = [holder.get_institution_name for holder in history.all()]
                add_items(key, items, self.result)

    def _format_title_in_database(self):
        medline_data = self.medline_titles
        add_items("v421", [medline.title for medline in medline_data], self.result)

    def _format_metadata(self):
        """Metadados e relacionamentos"""
        add_to_result("v91", self.obj.created.isoformat(), self.result)
        add_to_result("v122", Article.objects.count(), self.result)
        
    def _format_system_info(self):
        """Informações do sistema"""
        add_to_result("v200", '0', self.result)
        add_to_result("v991", '1', self.result)

    def _format_register_order_info(self):
        """Ordem do registro e por tipo do registro na base do fascículo e tipo do registro"""
        add_to_result("v700", '0', self.result)
        add_to_result("v701", '1', self.result)
        add_to_result("v706", 'i', self.result)

    def _format_field_use_system(self):
        """Campo usado no sistema"""
        if self.scielo_journal:
            field_value = f"{self.scielo_journal.journal_acron.upper()}{self.obj.volume}{self.obj.number}"
            add_to_result("v888", field_value, self.result)
    
    def _format_legend_bibliographic(self):
        """Formata a legenda bibliográfica complexa"""
        journal = self.obj.journal
        city = None
        
        if journal.contact_location and journal.contact_location.city:
            city = journal.contact_location.city.name
        
        journal_title = journal.title if journal.title else None
        
        volume_info = {
            'pt': f"v. {self.obj.volume}",
            'es': f"v. {self.obj.volume}",
            'en': f"vol. {self.obj.volume}"
        }
        
        number_info = {
            'pt': f"n. {self.obj.number}",
            'es': f"n. {self.obj.number}",
            'en': f"no. {self.obj.number}"
        }
        
        v43_entries = [
            {
                'l': lang,
                't': journal_title,
                'c': city,
                'v': volume_info[lang],
                'n': number_info[lang],
                'a': self.obj.year,
                'm': self.obj.season,
                '_': '',
            }
            for lang in ['pt', 'es', 'en']
        ]
        
        self.result["v43"].extend(v43_entries)

    def _format_supplement_info(self):
        """Informações de suplemento"""
        if not self.obj.number:
            add_to_result("v131", self.obj.supplement, self.result)
        else:
            add_to_result("v132", self.obj.supplement, self.result)

    def _format_title_summary(self):
        """Título do sumário"""
        self.result['v48'].extend([
            {'h': 'Sumário', 'l': 'pt', '_': ''},
            {'h': 'Table of Contents', 'l': 'en', '_': ''},
            {'h': 'Sumario', 'l': 'es', '_': ''}
        ])


def get_articlemeta_format_issue(obj):
    """
    Converte issue para formato ArticleMeta
    """
    formatter = ArticlemetaIssueFormatter(obj)
    return formatter.format()
