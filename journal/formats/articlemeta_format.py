from collections import defaultdict
from functools import lru_cache

from core.utils.articlemeta_dict_utils import add_items, add_to_result
from journal.models import SciELOJournal, TitleInDatabase


class ArticlemetaJournalFormatter:
    """Formatador para dados do ArticleMeta"""
    
    def __init__(self, obj, collection):
        self.obj = obj
        self.collection = collection
        self.result = defaultdict(list)
        self._scielo_journal = None
        self._medline_titles = None
        self.official = getattr(self.obj, 'official', None)

    @property
    def scielo_journal(self):
        if self._scielo_journal is not None:
            return self._scielo_journal

        qs = SciELOJournal.objects.select_related('collection', 'journal').filter(journal=self.obj)
        if self.collection:
            qs = qs.filter(collection__acron3=self.collection)

        self._scielo_journal = qs.first()
        return self._scielo_journal

    @property
    @lru_cache(maxsize=1)
    def titles_in_database_medline_secs(self):
        titles_in_db = TitleInDatabase.objects.filter(
                journal=self.obj,
                indexed_at__acronym__in=["medline", "secs"]
            ).select_related("indexed_at")
        return titles_in_db

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
            self._format_title_journal_info,
            self._format_scielo_journal_info,
            self._format_subject_areas_info,
            self._format_mission_info,
            self._format_contact_address_info,
            self._format_collection_info,
            self._format_journal_history,
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
            "v65": "<hr>",
            "v67": self.obj.user_subscription,
            "v110": self.obj.subtitle,
            "v130": self.obj.section,
            "v330": self.obj.level_of_publication,
            "v340": self.obj.alphabet,
            "v380": self.obj.frequency,
            "v550": self.obj.has_supplement,
            "v560": self.obj.is_supplement,
            "v692": self.obj.submission_online_url,
            "v699": self.obj.publishing_model,
        }
        for key, value in simple_fields.items():
            add_to_result(key, value, self.result)

        if acronym := getattr(self.obj.vocabulary, 'acronym', None): 
            add_to_result("v85", acronym, self.result)
        
        if license := getattr(self.obj.journal_use_license, 'license_type', None):
            add_to_result("v541", license, self.result)

        add_items("v64", [e.email for e in self.obj.journal_email.all()], self.result) 
        add_to_result("v117", self.obj.standard.code if self.obj.standard and self.obj.standard.code else None, self.result)
        add_items("v350", [lang.code2 for lang in self.obj.text_language.all()], self.result)
        add_items("v360", [lang.code2 for lang in self.obj.abstract_language.all()], self.result)
        add_items("v900", [annotation.notes for annotation in self.obj.notes.all()], self.result)

    def _format_contact_address_info(self):
        address = self.obj.contact_address
        try:
            add_items("v63", address.split("\n"), self.result)
        except Exception as e:
            add_to_result("v63", address, self.result)

    def _format_title_journal_info(self):
        """Informações do Title Journalal"""
        add_to_result("v150", self.obj.short_title, self.result)
        if iso_short_title := getattr(self.obj.official, 'iso_short_title', None):
            add_to_result("v151", iso_short_title, self.result)
        
        if parallel_titles := getattr(self.official, 'parallel_titles', None): 
            add_items("v230", [pt.text for pt in parallel_titles if pt.text], self.result)
        
        add_items("v240", [other_title.title for other_title in self.obj.other_titles.all()], self.result)
        add_items("v610", [old_title.title for old_title in self.official.old_title.all()], self.result)
        if title := getattr(self.official.new_title, 'title', None):
            add_to_result("v710", title, self.result)

    def _format_collection_info(self):
        if self.scielo_journal and self.scielo_journal.collection:
            collection = self.scielo_journal.collection
            if collection:
                acron3 = collection.acron3
                self.result["collection"] = acron3
                add_to_result("v690", collection.domain, self.result)
                add_to_result("v992", collection.acron3, self.result)

    def _format_scielo_journal_info(self):
        """Informações do SciELO Journal"""
        if self.scielo_journal:
            issn_scielo = self.scielo_journal.issn_scielo
            journal_acron = self.scielo_journal.journal_acron
            key_to_issn = {
                "v50": self.scielo_journal.status if self.scielo_journal.status else None,
                "v68": journal_acron,
                "v400": issn_scielo,
                "v880": issn_scielo,
                "v930": journal_acron.upper(),
            }
            for key, value in key_to_issn.items():
                add_to_result(key, value, self.result)

            self.result["code"] = issn_scielo

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
        """Informações do owner"""
        try:
            # Deixa preparado para tornar obsoleto o owner_history no modelo Journal
            owner_data = self.obj.owner_data
        except AttributeError:
            owner_data = {}
            owners = list(self.obj.owner_history.select_related(
                'institution__institution', 'institution__institution__location'
            ).all())
            for p in owners:
                owner_data["country_acronym"] = p.institution_country_acronym
                owner_data["state_acronym"] = p.institution_state_acronym
                owner_data["city_name"] = p.institution_city_name
                break
        add_items("v310", [owner_data.get("country_acronym")], self.result)
        add_items("v320", [owner_data.get("state_acronym")], self.result)
        add_items("v480", self.obj.owner_names, self.result)
        add_items("v490", [owner_data.get("city_name")], self.result)
        
    def _format_copyright_holder_info(self):
        """Informações do copyright holder"""
        # Primeiro tenta buscar do novo modelo JournalOrganization
        copyright_holders = self.obj.copyright_holders
        if copyright_holders:
            add_items("v62", copyright_holders, self.result)

    def _format_sponsor_info(self):
        """Informações do sponsor"""
        # Primeiro tenta buscar do novo modelo JournalOrganization
        sponsors = self.obj.sponsors
        if sponsors:
            add_items("v140", sponsors, self.result)

    def _format_indexing_info(self):
        """Informações de indexação"""
        # secs codes
        titles_in_db = self.titles_in_database_medline_secs
        medline_data = [t for t in titles_in_db if t.indexed_at.acronym.lower() == "medline"]
        secs_data = [t for t in titles_in_db if t.indexed_at.acronym.lower() == "secs"]
        add_items("v37", [sc.identifier for sc in secs_data if sc.identifier], self.result)
        title_medline = [m.title for m in medline_data]
        add_items("v420", [m.identifier for m in medline_data], self.result)
        add_items("v421", title_medline, self.result)

        indexeds_standard = [idx.name for idx in self.obj.indexed_at.all()]
        additional_indexed_at = [idx.name for idx in self.obj.additional_indexed_at.all()]
        add_items("v450", indexeds_standard + additional_indexed_at, self.result)
        self._format_wos_db_info()
        self._format_wos_area_info()

    def _format_wos_db_info(self):
        wos_db = self.obj.wos_db.all()
        key_to_code = {
            "v851": "SCIE",
            "v852": "SSCI",
            "v853": "A&HCI",
        }
        for key, code in key_to_code.items():
            add_items(key, [wos.code for wos in wos_db if wos.code == code], self.result)

    def _format_wos_area_info(self):
        add_items("v854", [wos.value for wos in self.obj.wos_area.all()], self.result)

    def _format_metadata(self):
        """Metadados diversos"""
        created = self.obj.created.strftime('%Y%m%d')
        updated = self.obj.updated.strftime('%Y%m%d')
        add_to_result("v940", created, self.result)
        add_to_result("v941", updated, self.result)
        add_to_result("v942", created, self.result)
        add_to_result("v943", updated, self.result)

        # tem que ser objeto datetime
        self.result["processing_date"] = self.obj.updated.strftime('%Y-%m-%d')
        self.result["created_at"] = self.obj.created.strftime('%Y-%m-%d')

    def _format_issn_info(self):
        """Informações de ISSN"""
        if self.official:
            issn_print = self.official.issn_print
            issn_electronic = self.obj.official.issn_electronic
            add_to_result("v935", issn_electronic, self.result)
            self._format_issn_list(issn_print, issn_electronic)
            self._format_issn_with_type(issn_print, issn_electronic)
            self._format_issn_type(issn_print)

    def _format_issn_list(self, issn_print, issn_electronic):
        if self.official:
            issns = [issn for issn in [issn_print, issn_electronic] if issn]
            self.result['issns'].extend(issns)
    
    def _format_issn_type(self, issn_print):
        if self.scielo_journal:
            if issn_print == self.scielo_journal.issn_scielo:
                type_issn = 'ONLIN'
                add_to_result("v35", type_issn, self.result)
            else:
                type_issn = "PRINT"
                add_to_result("v35", type_issn, self.result)

    def _format_issn_with_type(self, issn_print, issn_electronic):
        issns = []
        if issn_print:
            issns.append({"_": issn_print, "t": "PRINT"})
        if issn_electronic:
            issns.append({"_": issn_electronic, "t": "ONLIN"})
        self.result["v435"] = issns

    def _format_subject_areas_info(self):
        add_items("v440", [descriptor.value for descriptor in self.obj.subject_descriptor.all()], self.result)
        add_items("v441", [subject.code for subject in self.obj.subject.all()], self.result)

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
    
    def _former_dict_journal_history(self, subfield_a, subfield_b):
        dict_a = {
            "_": "",
            "a": subfield_a,
            "b": "C"
        }
        if subfield_b:
            dict_a.update({"d": subfield_b})
        return dict_a

    def _format_journal_history(self):
        if self.scielo_journal:
            journal_history = self.scielo_journal.journal_history.all()
            subfields = []
            subfield_b = ""
            for jh in journal_history:
                subfield_a = f"{jh.year}{jh.month}{jh.day or '01'}"
                if jh.interruption_reason:
                    subfield_b = "D" if jh.interruption_reason == "ceased" else "S"
                if jh.event_type == "ADMITTED":
                    dict_subfield =self._former_dict_journal_history(
                        subfield_a=subfield_a, 
                        subfield_b=subfield_b, 
                    )
                    subfields.append(dict_subfield)
                elif jh.event_type == "INTERRUPTED":
                    dict_subfield = self._former_dict_journal_history(
                        subfield_a=subfield_a, 
                        subfield_b=subfield_b, 
                    )
                    subfields.append(dict_subfield)

            self.result["v51"] =  subfields

def get_articlemeta_format_title(obj, collection):
    formatter = ArticlemetaJournalFormatter(obj, collection)
    return formatter.format()