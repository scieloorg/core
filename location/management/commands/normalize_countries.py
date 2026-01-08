import json
import logging
import re

import pycountry
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from rapidfuzz import fuzz, process

from location.models import Country, CountryMatched, State
from location.utils import (
    choose_canonical_country,
    clean_name,
    process_duplicates_countries,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normaliza dados de paises e carrega dados oficiais de paises"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Remove pontuação, acento, spaços extras"
        )
        parser.add_argument(
            "--unificate-country",
            action="store_true",
            help="Remove duplicidade de nomes de paises (Prioriza os registros mais completos)"
        )
        parser.add_argument(
            "--load-official-countries",
            action="store_true",
            help="Carrega nomes de países e atribuem eles como verificados."
        )
        parser.add_argument(
            "--load-official-states",
            action="store_true",
            help="Carrega nomes de países e atribuem eles como verificados."
        )        
        parser.add_argument(
            "--fuzzy-match-countries",
            type=int,
            help="Faz fuzzy matching entre países CLEANED e official"
        )
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Reprocessa países já processados"
        )        
    def handle(self, *args, **options):
        if not any(options.values()):
            raise CommandError(
                "Informe ao menos uma ação: "
                "--clean, --unificate-country ou --load-official-countries"
            )

        if options['clean']:
            self.stdout.write("Limpando nomes de países...")
            self.clean_name_countries()
        if options['unificate_country']:
            self.stdout.write("Unificando países...")
            self.unificate_countries()
        if options['load_official_countries']:
            self.stdout.write("Carregando países verificados...")
            self.load_official_countries()
        if options['load_official_states']:
            self.stdout.write("Carregando Estados verificados...")
            self.load_official_states()
        if options['load_official_states']:
            self.stdout.write("Carregando Cidades verificados...")
            self.load_official_cities()  
        if options['fuzzy_match_countries']:
            fuzzy_params = options["fuzzy_match_countries"]
            reprocess = options["reprocess"]
            self.stdout.write(f"Realizando matched dos paises que não sao verificados com verificados...threshold: {fuzzy_params}")
            self.auto_create_fuzzy_matches(threshold=fuzzy_params, reprocess=reprocess)


    def clean_name_countries(self):
        countries = Country.objects.filter(name__isnull=False)

        for country in countries:
            name_country = country.name
            if clean_name(name_country) == country.name:
                continue
            country.name = clean_name(name_country)
            country.status = "CLEANED"
            country.save()
    
    def unificate_countries(self):
        duplicate_names = (
            Country.objects.filter(status="CLEANED")
            .values("name")
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        total_merged = 0
        total_deleted = 0

        for item in duplicate_names:
            name = item['name']
            try:
                with transaction.atomic():
                    countries_with_same_name = Country.objects.filter(name=name, status="CLEANED").order_by('created', 'id')
                    if countries_with_same_name.count() <= 1:
                        continue
                    # Escolher o país canonical
                    # Prioridade: 1) com acronym e acron3, 2) com acronym, 3) mais antigo
                    canonical_country = choose_canonical_country(countries_with_same_name)
                    duplicates = countries_with_same_name.exclude(id=canonical_country.id)
                    logging.info(f"Duplicate IDs: {duplicates.values('names', 'id')}")
                    locations_moved = process_duplicates_countries(duplicates=duplicates, canonical_country=canonical_country, total_deleted=total_deleted)
                    canonical_country.save()
                logging.info(f"'{name}': {duplicates.count()} duplicatas removidas, {locations_moved} locations atualizados")
                total_merged += 1
            except Exception as e:
                logging.error(f"Error ao processar {name}: {e}")
                continue
    
    def load_official_countries(self):
        countries = pycountry.countries

        for py_country in countries:
            name = py_country.name
            acron2 = py_country.alpha_2
            acron3 = py_country.alpha_3
            try:
                country = Country.objects.get(name__iexact=name, acronym=acron2)
                country.status = "OFFICIAL"
                country.save()
            except Country.DoesNotExist:
                Country.objects.create(
                    name=name,
                    acronym=acron2,
                    acron3=acron3,
                    status="OFFICIAL"
                )

    def auto_create_fuzzy_matches(self, threshold, reprocess=None):
        matches = self.fuzzy_match_countries(threshold=threshold, reprocess=reprocess)
        created_count = 0
        high_confidence_count = 0

        for match_data in matches:
            unmatched = match_data['unmatched']
            official = match_data['official']
            score = match_data['score']
            # confidence = match_data['confidence']   
            if score >= threshold:
                country_match, created = CountryMatched.objects.get_or_create(
                    official=official,
                )
                unmatched.status = "MATCHED"
                unmatched.save()
                country_match.matched.add(unmatched)
                country_match.score = threshold
                country_match.save()

                created_count += 1

        logging.info(f"Total matches: {created_count}")
        logging.info(f"Auto-applied: {high_confidence_count}")

        return matches

    def apply_fuzzy_matched_countries(self, name=None):
        if name:
            countries_official = Country.objects.filter(name=name, status="official")
        else:
            countries_official = Country.objects.filter(status="official")
        
        for country in countries_official:
            logging.info(f"Apply fuzzy matched for {country.name}")
            country_matched = CountryMatched.objects.get(official=country)
            locations_count = country_matched.apply_to_locations()
            matched = country_matched.matched.all()
            matched.update(status="PROCESSED")
            logging.info(f"Total processed matches: {locations_count} {matched.values_list('name', flat=True)}")

    def unset_matched_countries(self, name=None):
        if name:
            countries_official = Country.objects.filter(name=name, status="official")
        
        for country in countries_official:
            country_matched = CountryMatched.objects.get(official=country)
            unset_countries = country_matched.unset_matched_countries()
            logging.info(f"unset matched countries {country}: {unset_countries}")            
            

    def fuzzy_match_countries(self, threshold=85, reprocess=None):
        """
        Faz fuzzy matching entre países CLEANED e official
        Args:
            threshold: Score mínimo para considerar um match (0-100)
            reprocess: Se True, incluir países com status "MATCHED" para reprocessamento,
                    senão considerar apenas "CLEANED"

        Returns:
            list: Lista de matches encontrados.
        """
        official_countries = Country.objects.filter(status="OFFICIAL")
        if reprocess:
            CountryMatched.objects.all().delete()
            status = ["MATCHED", "CLEANED"]
        else:
            status = ["CLEANED"]
        unmatched_countries = Country.objects.filter(status__in=status)

        matches_found = []
        official_names = {c.name: c for c in official_countries}
        for unmatched in unmatched_countries:
            result = process.extractOne(
                unmatched.name,
                official_names.keys(),
                scorer=fuzz.WRatio,
                score_cutoff=threshold,
            )
            if result:
                matched_name, score, _ = result
                official = official_names[matched_name]
                
                matches_found.append({
                    'unmatched': unmatched,
                    'official': official,
                    'score': score,
                    'confidence': score / 100.0
                    }
                )
                #TODO
                #REJECTED
                logging.info(
                    f"Match: {unmatched.name} -> {official.name}"
                    f"(score: {score})"
                )
        return matches_found