from collections import defaultdict
from functools import lru_cache

from article.models import Article
from core.utils.articlemeta_dict_utils import add_items, add_to_result
from journal.models import SciELOJournal, TitleInDatabase
from journal.formats.articlemeta_format import ArticlemetaJournalFormatter

class ArticlemetaIssueFormatter:
    """Formatador para dados do Issue"""
    def __init__(self, obj):
        self.obj = obj
        self.result = defaultdict(list)
        self.result['issue'] = {}
        self.journal = self.obj.journal
        self._scielo_journal = None
        self._medline_titles = None
        self.article = Article.objects.filter(issue=self.obj, journal=self.journal)
    
    @property
    def scielo_journal(self):
        if self._scielo_journal is None:
            self._scielo_journal = SciELOJournal.objects.select_related(
                'journal', 'collection'
            ).filter(
                journal=self.journal,
            ).first()
        return self._scielo_journal

    @property
    @lru_cache(maxsize=1)
    def medline_titles(self):
        return list(TitleInDatabase.objects.filter(
            journal=self.journal, 
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
            self._format_title_in_database,
            self._format_collection_info,
            self._format_article_info,
            self._format_issn_info,
        ]
        
        for formatter in formatters:
            formatter()
        
        return dict(self.result)

    def _format_basic_info(self):
        """Informações básicas do issue"""
        # Path to base issue
        key_to_code = {
            "v31": self.obj.volume,
            "v32": self.obj.number,
            "v36": f"{self.obj.year}{self.obj.number}" if self.obj.number else self.obj.year,
            "v42": '1',
        }
        for key, value in key_to_code.items():
            add_to_result(key, value, self.result['issue'])
        # "v6": Ordem de publicação dos fascículos para apresentação na interface

        if hasattr(self.obj, 'issue_title'):
            add_items("v33", [title for title in self.obj.issue_title.all()], self.result['issue'])
        
        # Part (dado fixo)
        self.result["v34"].append({"_": None})
        self._format_volume_supplement_number_info()
        self._format_issue_type()

    def _format_volume_supplement_number_info(self):
        volume = self.obj.volume
        number = self.obj.number
        supplement = self.obj.supplement

        if volume:
            if number:
                v4 = f"v{volume}n{number}"
            elif supplement:
                v4 = f"v{volume}s{supplement}"
            else:
                v4 = f"v{volume}"
            self.result['issue']["v4"] = v4

    def _format_issue_type(self):
        if self.obj.supplement and not self.obj.number:
            self.result["issue_type"] = "supplement"


    def _format_publication_info(self):
        """Informações de publicação"""
        year = self.obj.year
        month = self.obj.month
        
        if year and month:
            self.result['issue']["v64"] = {"a": year, "m": month}
            add_to_result("v65", year + month + '00', self.result['issue'])
        elif year:
            self.result['issue']["v64"] = {"a": year}
            add_to_result("v65", year + '0000', self.result['issue'])

    def _format_collection_info(self):
        """Informações de coleção"""
        collection = self.scielo_journal.collection
        if collection:
            key_to_code = {
                "v992": collection.acron3,
            }
            for key, value in key_to_code.items():
                add_to_result(key, value, self.result['issue'])
            self.result['collection'] = collection.acron3
            self.result['issue']['collection'] = collection.acron3

    def _format_journal_info(self):
        """Informações do journal"""
        key_to_code = {
            "v30": self.journal.short_title,
            "v130": self.journal.title,
            "v117": self.journal.standard.code if self.journal.standard else None,
        }
        for key, value in key_to_code.items():
            add_to_result(key, value, self.result['issue'])
        
        if self.journal and self.journal.journal_use_license:
            add_to_result("v541", self.journal.journal_use_license.license_type, self.result['issue'])

        if self.scielo_journal:
            add_to_result("v930", self.scielo_journal.journal_acron.upper() if self.scielo_journal.journal_acron else None, self.result['issue'])
        
        if self.journal.vocabulary:
            add_to_result("v85", self.journal.vocabulary.acronym, self.result['issue'])

        if self.journal.official and self.journal.official.iso_short_title:
            add_to_result("v151", self.journal.official.iso_short_title, self.result['issue'])

        if self.journal.official and hasattr(self.journal.official, 'parallel_titles'):
            add_items("v230", [pt.text for pt in self.journal.official.parallel_titles if pt.text], self.result['issue'])


    def _format_institution_info(self):
        """Informações de instituições"""
        history = {
            "v62": "copyright_holder_history",
            "v140": "sponsor_history",
            "v480": "publisher_history"
        }

        for key, attr in history.items():
            history = getattr(self.journal, attr, None)
            if history:
                items = [holder.institution_name for holder in history.all()]
                add_items(key, items, self.result['issue'])

    def _format_title_in_database(self):
        medline_data = self.medline_titles
        add_items("v421", [medline.title for medline in medline_data], self.result['issue'])

    def _format_metadata(self):
        """Metadados e relacionamentos"""
        key_to_code = {
            "publication_date": self.obj.year,
            "publication_year": self.obj.year,
            "created_at": self.obj.created.strftime("%Y-%m-%d"),
            "processing_date": self.obj.created.strftime("%Y-%m-%d"),
        }
        for key, value in key_to_code.items():
            self.result[key] = value

        self.result['issue']["processing_date"] = self.obj.created.strftime("%Y-%m-%d")
        add_to_result("v91", self.obj.created.strftime("%Y%m%d"), self.result['issue'])

    def _format_system_info(self):
        """Informações do sistema"""
        key_to_code = {
            "v200": '0',
            "v991": '1',
        }
        for key, value in key_to_code.items():
            add_to_result(key, value, self.result['issue'])

    def _format_register_order_info(self):
        """Ordem do registro e por tipo do registro na base do fascículo e tipo do registro"""
        key_to_code = {
            "v700": '0',
            "v701": '1',
            "v706": 'i',
        }
        for key, value in key_to_code.items():
            add_to_result(key, value, self.result['issue'])


    def _format_field_use_system(self):
        """Campo usado no sistema"""
        if self.scielo_journal:
            field_value = f"{self.scielo_journal.journal_acron.upper()}{self.obj.volume}{self.obj.number}"
            add_to_result("v888", field_value, self.result['issue'])
    
    def _format_legend_bibliographic(self):
        """Formata a legenda bibliográfica complexa"""
        city = None
        
        if self.journal and self.journal.contact_location and self.journal.contact_location.city:
            city = self.journal.contact_location.city.name
        
        journal_title = self.journal.title if self.journal.title else None

        v43_entries = []
        for lang in ['pt', 'es', 'en']:
            entry = {
                'l': lang,
                't': journal_title,
                'c': city,
                'a': self.obj.year,
                '_': '',
            }
            # Só adiciona 'v' se houver volume
            if self.obj.volume:
                entry['v'] = f'vol.{self.obj.volume}'
            # Só adiciona 'n' se houver number
            if self.obj.number:
                entry['n'] = f'no.{self.obj.number}'
            if self.obj.season:
                entry['m'] = self.obj.season
            if self.obj.supplement:
                entry['w'] = f"suppl.{self.obj.supplement}"
            v43_entries.append(entry)
        
        self.result['issue']["v43"] = v43_entries

    def _format_supplement_info(self):
        """Informações de suplemento"""
        if not self.obj.number:
            add_to_result("v131", self.obj.supplement, self.result['issue'])
        else:
            add_to_result("v132", self.obj.supplement, self.result['issue'])

    def _format_title_summary(self):
        """Título do sumário"""
        self.result['issue']['v48'] = [
            {'h': 'Sumário', 'l': 'pt', '_': ''},
            {'h': 'Table of Contents', 'l': 'en', '_': ''},
            {'h': 'Sumario', 'l': 'es', '_': ''}
        ]

    def _format_article_info(self):
        """Informações de artigo"""
        if self.article.exists():
            code = self.article.first().pid_v2[1:]
            key_to_code = {
                "v122": str(self.obj.article_set.count()),
                "v880": self.article.first().pid_v2[1:],
            }
            for key, value in key_to_code.items():
                add_to_result(key, value, self.result['issue'])
            
            self.result['issue']['code'] = code
            self.result['code'] = code
            

    def _format_issn_info(self):
        """Informações de edição"""
        if self.scielo_journal:
            issn_print = self.scielo_journal.journal.official.issn_print
            issn_electronic = self.scielo_journal.journal.official.issn_electronic
            issn_scielo = self.scielo_journal.issn_scielo
            key_to_code = {
                "v35": issn_scielo,
                "v935": issn_electronic,
            }
            for key, value in key_to_code.items():
                add_to_result(key, value, self.result['issue'])        
            
            self._format_issn_with_type(issn_print, issn_electronic)
            self._format_issn_code_title(issn_print, issn_electronic)

    def _format_issn_with_type(self, issn_print, issn_electronic):
        """Informações de ISSN com tipo"""
        issns = []
        if issn_print:
            issns.append({"_": issn_print, "t": "PRINT"})
        if issn_electronic:
            issns.append({"_": issn_electronic, "t": "ONLIN"})
        self.result['issue']["v435"] = issns

    def _format_issn_code_title(self, issn_print, issn_electronic):
        self.result['code_title'] = [
            issn_electronic,
            issn_print,
        ]

def get_articlemeta_format_issue(obj):
    """
    Converte issue para formato ArticleMeta
    """
    formatter_issue = ArticlemetaIssueFormatter(obj).format()
    formatter_journal = ArticlemetaJournalFormatter(obj.journal).format()
    formatter = formatter_issue.update(formatter_journal)
    return formatter
