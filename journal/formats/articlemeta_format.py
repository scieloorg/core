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
        self._copyright_holder_history = None
        self._sponsor_history = None
        self.official = getattr(self.obj, 'official', None)

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
    def sponsor_history(self):
        if self._sponsor_history is None:
            self._sponsor_history = self.obj.sponsor_history.select_related(
                'institution__institution', 'institution__institution__location'
            ).all()
        return self._sponsor_history
    
    @property
    def copyright_holder_history(self):
        if self._copyright_holder_history is None:
            self._copyright_holder_history = self.obj.copyright_holder_history.select_related(
                'institution__institution', 'institution__institution__location'
            ).all()
        return self._copyright_holder_history

    @property
    @lru_cache(maxsize=1)
    def medline_titles(self):
        return list(TitleInDatabase.objects.filter(
            journal=self.obj, 
            indexed_at__acronym__iexact="medline"
        ).select_related("indexed_at"))
    
    @property
    @lru_cache(maxsize=1)
    def secs_codes(self):
        return list(TitleInDatabase.objects.filter(
            journal=self.obj,
            indexed_at__acronym__iexact="secs"
        ).select_related("indexed_at"))

    def format(self):
        """Formata todos os dados do journal"""
        formatters = [
            self._format_basic_info,
            self._format_publication_info,
            self._format_publisher_info,
            self._format_copyright_holder_info,
            self._format_sponsor_info,
            self._format_indexing_info,
            self._format_metadata,
            self._format_issn_info,
            self._format_title_jorunal_info,
            self._format_scielo_journal_info,
            self._format_subject_areas_info,
            self._format_mission_info,
        ]
        
        for formatter in formatters:
            formatter()
        
        return dict(self.result)

    def _format_basic_info(self):
        """Informações básicas do journal"""
        simple_fields = {
            "v5": self.obj.type_of_literature,
            "v6": self.obj.treatment_level,
            "v10": self.obj.center_code,
            "v20": self.obj.national_code,
            "v30": self.obj.identification_number,
            "v66": self.obj.ftp,
            "v67": self.obj.user_subscription,
            "v110": self.obj.subtitle,
            "v130": self.obj.section,
            "v330": self.obj.level_of_publication,
            "v340": self.obj.alphabet,
            "v380": self.obj.frequency,
            "v550": self.obj.has_supplement,
            "v560": self.obj.is_supplement,
        }
        for key, value in simple_fields.items():
            add_to_result(key, value, self.result)

        if self.scielo_journal and self.scielo_journal.status:
            add_to_result("v50", self.scielo_journal.status.lower(), self.result)

        if acronym := getattr(self.obj.vocabulary, 'acronym', None): 
            add_to_result("v85", acronym, self.result)
        add_to_result("v117", self.obj.standard.code if self.obj.standard and self.obj.standard.code else None, self.result)
        add_items("v350", [lang.code2 for lang in self.obj.text_language.all()], self.result)
        add_items("v360", [lang.code2 for lang in self.obj.abstract_language.all()], self.result)
        add_items("v900", [annotation.notes for annotation in self.obj.annotation.all()], self.result)

    def _format_title_jorunal_info(self):
        """Informações do Title Journalal"""
        add_to_result("v150", self.obj.short_title, self.result)

        if parallel_titles := getattr(self.official, 'parallel_titles', None): 
            add_items("v230", [pt.text for pt in parallel_titles if pt.text], self.result)
        
        add_items("v240", [other_title.title for other_title in self.obj.other_titles.all()], self.result)
        add_items("v610", [old_title.title for old_title in self.official.old_title.all()], self.result)
        if title := getattr(self.official.new_title, 'title', None):
            add_to_result("v710", self.official.new_title.title, self.result)

    def _format_scielo_journal_info(self):
        """Informações do SciELO Journal"""
        add_to_result("collection", self.scielo_journal.collection.acron3 if self.scielo_journal.collection else None, self.result)
        add_to_result("code", self.scielo_journal.issn_scielo if self.scielo_journal else None, self.result)
        if hasattr(self.scielo_journal, 'journal_acron'):
            add_to_result("v68", self.scielo_journal.journal_acron, self.result)

    def _format_publication_info(self):
        """Informações de publicação"""
        if self.official:
            add_to_result("v100", self.official.title, self.result)
            add_to_result("v301", self.official.initial_year, self.result)
            add_to_result("v302", self.official.initial_volume, self.result)
            add_to_result("v303", self.official.initial_number, self.result)
            
            year = self.official.terminate_year
            month = self.official.terminate_month

            if month and year:
                add_to_result("v304", year + month, self.result)
            elif year:
                add_to_result("v304", year, self.result)

            add_to_result("v305", self.official.final_volume, self.result)
            add_to_result("v306", self.official.final_number, self.result)

    def _format_publisher_info(self):
        """Informações do publisher"""
        publishers = list(self.publisher_history)
        
        add_items("v310", [p.institution_country_name for p in publishers], self.result)
        add_items("v320", [p.instition_state_acronym for p in publishers], self.result)
        add_items("v480", [p.institution_name for p in publishers], self.result)
        add_items("v490", [p.institution_city_name for p in publishers], self.result)
    
    def _format_copyright_holder_info(self):
        """Informações do copyright holder"""
        copyright_holders = list(self.copyright_holder_history)
        add_items("v62", [p.institution_country_name for p in copyright_holders], self.result)

    def _format_sponsor_info(self):
        """Informações do sponsor"""
        sponsors = list(self.sponsor_history)
        add_items("v140", [p.institution_country_name for p in sponsors], self.result)

    def _format_indexing_info(self):
        """Informações de indexação"""
        # secs codes
        secs_code = self.secs_codes
        add_items("v37", [sc.identifier for sc in secs_code if sc.identifier], self.result)
        
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

    def _format_issn_info(self):
        """Informações de ISSN"""
        if self.official:
            issn_print = self.obj.official.issn_print
            issn_electronic = self.obj.official.issn_electronic 
            self._format_issn_list(issn_print, issn_electronic)
            self._format_issn_with_type(issn_print, issn_electronic)
    
    def _format_issn_list(self, issn_print, issn_electronic):
        if self.official:
            issns = [issn for issn in [issn_print, issn_electronic] if issn]
            self.result['issns'].extend(issns)
    
    def _format_issn_with_type(self, issn_print, issn_electronic):
        issns = []
        if issn_print:
            issns.append({"_": issn_print, "t": "PRINT"})
        if issn_electronic:
            issns.append({"_": issn_electronic, "t": "ONLIN"})
        self.result["v435"] = issns

    def _format_subject_areas_info(self):
        add_items("v440", [descriptor.value for descriptor in self.obj.subject_descriptor.all()], self.result)
        add_items("v441", [subject.value for subject in self.obj.subject.all()], self.result)

    def _format_mission_info(self):
        if not hasattr(self.obj, 'mission') or not self.obj.mission.exists():
            return
            
        missions_data = []
        for mission in self.obj.mission.select_related('language'):
            if mission.language and mission.get_text_pure:
                missions_data.append({
                    "l": mission.language.code2,
                    "_": mission.get_text_pure
                })
        
        if missions_data:
            self.result["v901"] = missions_data

def get_articlemeta_format_title(obj):
    formatter = ArticlemetaJournalFormatter(obj)
    return formatter.format()