from locale import normalize
import logging

from django.core.management.base import BaseCommand, CommandError
from rapidfuzz import fuzz, process

from collection.models import Collection
from core.utils.rename_dictionary_keys import rename_dictionary_keys
from core.utils.utils import _get_user
from journal.models import AMJournal, SciELOJournal
from journal.sources.am_field_names import correspondencia_journal
from location import utils
from location.models import Country, State, City, Location
from django.db.models import Q
from journal.sources.am_data_extraction import extract_value
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reexecuta instituições para obter localização normalizada."

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-locations-linked-with-institutions",
            action="store_true",
            help="Deleta localização de institutições (Publisher, Owner, Sponsor, Copyright)"
        )
        parser.add_argument(
            "--delete-institutions",
            action="store_true",
            help="Deleta instituições vinculado aos periódicos"
        )
        parser.add_argument(
            "--update-am-journals",
            type=str,
            help="Atualiza periódicos"
        )
        parser.add_argument(
            "--reload-institutions",
            type=str,
            help="Atualiza periódicos"
        )


    def handle(self, *args, **options):
        if not any(options.values()):
            raise CommandError(
                "Informe ao menos uma ação: "
                "--delete-locations-linked-with-institutions, --delete-institutions"
            )
        if options['delete_locations_linked_with_institutions']:
            self.stdout.write("Excluindo localizações de instituições;")
            
        if options["delete_institutions"]:
            self.stdout.write("Excluindo instituições para recarregar.")
        if options["update_am_journals"]:
            self.stdout.write("Excluindo instituições para recarregar.")
            self.update_am_journal(username=options["update_am_journals"])
        if options["reload_institutions"]:
            self.stdout.write("Atualizando localização de instituições e criando novas localizações officiais.")
            self.replace_locations_official_linked_institutions(username=options["reload_institutions"])            


    def update_am_journal(self, username):
        from journal.tasks import process_journal_article_meta
        user = _get_user(request=None, username=username, user_id=None)
        items = Collection.objects.filter(collection_type="journals").iterator()
        for item in items:
            process_journal_article_meta(user=user, limit=None, collection=item.acron3)

    def replace_locations_official_linked_institutions(self, username):
        am_journals = AMJournal.objects.all()
        for am_journal in am_journals:
            try:
                scielo_journal = SciELOJournal.objects.filter(issn_scielo=am_journal.pid)
            except SciELOJournal.DoesNotExist:
                continue
            if am_journal.data:
                journal_dict = rename_dictionary_keys(
                        am_journal.data, correspondencia_journal
                    )
                country_name = extract_value(journal_dict.get("publisher_country"))
                state_name = extract_value(journal_dict.get("publisher_state"))
                city_name = extract_value(journal_dict.get("publisher_city"))
                print(country_name, state_name, city_name)

    
    def replace_location_publisher(self, scielo_journal, new_location):
        journal = scielo_journal.journal
        if publisher_history := journal.publisher_history.all():
            for ph in publisher_history:
                if ph.institution and ph.institution.institution:
                    logging.info(f"Atualizando localização de {ph.institution.institution}")
                    ph.institution.institution.location = new_location
                    ph.institution.institution.save()

    def normalize_location(self, country, state, city):
        normalize_country = self.normalize_country(country=country)
        normalize_state = self.normalize_state(state=state)
        normalize_city = self.normalize_city(city=city)
        logging.info(normalize_country, normalize_state, normalize_city)
        if normalize_country:
            country = self.get_official_country(name=normalize_country)
        if normalize_state:
            state = self.get_official_state(name=normalize_state)
        if normalize_city:
            city = self.get_official_city(name=normalize_city)
        return {
            'country': country,
            'state': state,
            'city': city,
        }

    def create_location(self, country, state, city):
        location, created = Location.objects.get_or_create(
            country=country,
            state=state,
            city=city
        )
        if all([
            country is not None and getattr(country, "status", None) == "OFFICIAL",
            state is not None and getattr(state, "status", None) == "OFFICIAL",
            city is not None and getattr(city, "status", None) == "OFFICIAL"
        ]):
            location.status = "OFFICIAL"
            location.save()
        return location, created


    def get_official_country(self, name):
        fuzz_match = self.fuzzy_match(name=name, type_obj_location=Country)
        logging.info(f"Country name fuzz: {fuzz_match}. name: {name}")
        try:
            return Country.objects.get(Q(name=name) | Q(acronym__iexact=name), status="OFFICIAL")
        except Country.DoesNotExist:
            country, _ = Country.objects.get_or_create(Q(name=name) | Q(acronym__iexact=name))
            return country
    
    def get_official_state(self, name):
        fuzz_match = self.fuzzy_match(name=name, type_obj_location=State)
        name = fuzz_match        
        try:
            return State.objects.get(Q(name=name) | Q(acronym__iexact=name), status="OFFICIAL")
        except State.DoesNotExist:
            state, _ = State.objects.get_or_create(Q(name=name) | Q(acronym__iexact=name))
            return state

    def get_official_city(self, name):
        city, _ = City.objects.get_or_create(name=name)
        return city

    def normalize_country(self, country):
        country = utils.clean_name(country)

    def normalize_state(self, state):
        state = utils.clean_name(state)

    def normalize_city(self, city):
        city = utils.clean_name(city)
    
    def fuzzy_match(self, name, type_obj_location, threshold=85):
        matches_found = []
        official = type_obj_location.objects.filter(status="OFFICIAL")
        official_names = {c.name: c for c in official}

        result = process.extractOne(
            name,
            official_names.keys(),
            scorer=fuzz.WRatio,
            score_cutoff=threshold,
        )
        if result:
            matched_name, score, _ = result
            official = official_names[matched_name]
            matches_found.append({
                'unmatched': name,
                'official': official,
                'score': score,
                }
            )
        return name
