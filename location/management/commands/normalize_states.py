import json
import logging
import re

import pycountry
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import Count
from rapidfuzz import fuzz, process

from location.models import Country, State, StateMatched
from location.utils import choose_canonical_state, clean_name, process_duplicates_states, clean_acronym

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normaliza dados de estados e carrega dados oficiais de estados"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Remove pontuação, acento, espaços extras dos estados"
        )
        parser.add_argument(
            "--unificate-states",
            action="store_true",
            help="Remove duplicidade de nomes de estados"
        )
        parser.add_argument(
            "--load-official-states",
            action="store_true",
            help="Carrega nomes de estados oficiais do pycountry"
        )
        parser.add_argument(
            "--fuzzy-match-states",
            type=int,
            help="Faz fuzzy matching entre estados CLEANED e OFFICIAL"
        )
        parser.add_argument(
            "--apply-matches",
            action="store_true",
            help="Aplica os matches aos locations"
        )
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Reprocessa estados já processados"
        )

    def handle(self, *args, **options):
        if not any(options.values()):
            raise CommandError(
                "Informe ao menos uma ação: "
                "--clean, --unificate-states, --load-official-states, "
                "--fuzzy-match-states, ou --apply-matches"
            )

        if options['clean']:
            self.stdout.write("Limpando nomes de estados...")
            self.clean_name_states()
        
        if options['unificate_states']:
            self.stdout.write("Unificando estados...")
            self.unificate_states()
        
        if options['load_official_states']:
            self.stdout.write("Carregando estados verificados...")
            self.load_official_states()
        
        if options['fuzzy_match_states']:
            fuzzy_params = options["fuzzy_match_states"]
            reprocess = options["reprocess"]
            self.stdout.write(f"Realizando matched dos estados...threshold: {fuzzy_params}")
            self.auto_create_fuzzy_matches_states(threshold=fuzzy_params, reprocess=reprocess)
        
        if options['apply_matches']:
            self.stdout.write("Aplicando matches aos locations...")
            self.apply_fuzzy_matched_states()

    def clean_name_states(self):
        """Limpa nomes de estados (remove HTML, pontuação, normaliza espaços)"""
        states = State.objects.filter(name__isnull=False)
        count = 0
        deleted = 0
        
        for state in states:
            name_state = state.name
            acronym_state = state.acronym
            cleaned_name = clean_name(name_state)
            cleaned_acronym = clean_acronym(acronym_state)
            if cleaned_name == name_state and cleaned_acronym == acronym_state:
                continue
            
            try:
                with transaction.atomic():
                    state.name = cleaned_name
                    state.acronym = cleaned_acronym
                    state.status = "CLEANED"
                    state.save()
                    logging.info(f"Nome de estado limpado {name_state} -> {state.name}")
                    count += 1
            except IntegrityError:
                # Estado duplicado já existe com esse nome limpo
                logging.info(f"Estado duplicado após limpeza: {name_state} -> {cleaned_name}, deletando...")
                try:
                    state.delete()
                    deleted += 1
                except Exception as e:
                    logging.error(f"Erro ao deletar estado {state.id}: {e}")
        
        self.stdout.write(self.style.SUCCESS(f"✓ {count} estados limpos, {deleted} duplicados removidos"))
        
        self.stdout.write(self.style.SUCCESS(f"✓ {count} estados limpos"))

    def unificate_states(self):
        """Unifica estados duplicados mantendo o mais completo"""
        duplicate_names = (
            State.objects.filter(status="CLEANED")
            .values("name")
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        logging.info(f"Quantidade de estados duplicados: {duplicate_names.count()} Estados: {duplicate_names}")
        total_merged = 0
        total_deleted = 0
        for item in duplicate_names:
            name = item['name']
            try:
                with transaction.atomic():
                    states_with_same_name = State.objects.filter(
                        name=name, 
                        status="CLEANED"
                    ).order_by('created', 'id')
                    
                    if states_with_same_name.count() <= 1:
                        continue
                    
                    canonical_state = choose_canonical_state(states_with_same_name)
                    
                    duplicates = states_with_same_name.exclude(id=canonical_state.id)
                    
                    logging.info(f"Duplicate IDs: {duplicates.values_list('name', 'id')}")
                    locations_moved = process_duplicates_states(
                        duplicates=duplicates, 
                        canonical_state=canonical_state, 
                        total_deleted=total_deleted
                    )
                    canonical_state.save()
                    
                logging.info(
                    f"'{name} ({canonical_state.acronym if canonical_state else None})': {duplicates.count()} duplicatas removidas, "
                    f"{locations_moved} locations atualizados"
                )
                total_merged += 1
            except Exception as e:
                logging.error(f"Erro ao processar {name} ({canonical_state.acronym if canonical_state else None}): {e}")
                continue
        
        self.stdout.write(self.style.SUCCESS(
            f"✓ {total_merged} grupos de estados unificados, {total_deleted} deletados"
        ))

    def get_country_subdivision(self, country_code):
        """Busca subdivisões (estados) de um país no pycountry"""
        subdivisions = []

        try:
            for subdivision in pycountry.subdivisions.get(country_code=country_code):
                subdivisions.append({
                    'code': subdivision.code,
                    'name': subdivision.name,
                    'type': subdivision.type,
                    'country_code': subdivision.country_code,
                })
        except KeyError:
            subdivisions.append({
                'country_code': country_code
            })
        return subdivisions

    def load_official_states(self):
        """Carrega estados oficiais do pycountry para países OFFICIAL"""
        for country_official in Country.objects.filter(status="OFFICIAL"):
            try:
                subdivisions = self.get_country_subdivision(country_code=country_official.acronym)
                logging.info(f"Carregando estados para {country_official}")
                for sub in subdivisions:
                    if 'code' not in sub:
                        continue
                    # Extrair a sigla. Ex: PT-CE -> CE
                    acronym = sub['code'].split('-')[-1]
                    name = sub['name']
                    state, created = State.objects.get_or_create(
                        name=name,
                        acronym=acronym,
                        defaults={'status': "OFFICIAL"},
                    )
                    if not created and state.status != "OFFICIAL":
                        state.status = "OFFICIAL"
                        state.save(update_fields=["status"])
            except Exception as e:
                logging.error(e)
                logging.error(f"Estado do País {country_official} não criado.")
                continue

    def fuzzy_match_states(self, threshold=85, reprocess=None):
        """Faz fuzzy matching entre estados CLEANED e OFFICIAL
        
        Args:
            threshold: Score mínimo para considerar um match (0-100)
            reprocess: Se True, reprocessa estados com status MATCHED
        
        Returns:
            list: Lista de matches encontrados
        """
        official_states = State.objects.filter(status="OFFICIAL")
        
        if reprocess:
            StateMatched.objects.all().delete()
            status = ["MATCHED", "CLEANED"]
        else:
            status = ["CLEANED"]
        
        unmatched_states = State.objects.filter(status__in=status)
        matches_found = []
        
        # Criar dict de estados oficiais por (name, acronym)
        official_dict = {
            f"{s.name}|{s.acronym}": s 
            for s in official_states 
            if s.name and s.acronym
        }
        
        for unmatched in unmatched_states:
            if not unmatched.name:
                continue
            
            search_key = f"{unmatched.name}|{unmatched.acronym or ''}"
            
            result = process.extractOne(
                search_key,
                official_dict.keys(),
                scorer=fuzz.WRatio,
                score_cutoff=threshold,
            )
            
            if result:
                matched_key, score, _ = result
                official = official_dict[matched_key]
                
                matches_found.append({
                    'unmatched': unmatched,
                    'official': official,
                    'score': score,
                    'confidence': score / 100.0
                })
                
                logging.info(
                    f"Match: {unmatched.name} ({unmatched.acronym}) -> "
                    f"{official.name} ({official.acronym}) (score: {score})"
                )
        
        return matches_found

    def auto_create_fuzzy_matches_states(self, threshold, reprocess=None):
        """Cria automaticamente matches entre estados não oficiais e oficiais"""
        matches = self.fuzzy_match_states(threshold=threshold, reprocess=reprocess)
        created_count = 0
        
        for match_data in matches:
            unmatched = match_data['unmatched']
            official = match_data['official']
            score = match_data['score']
            
            if score >= threshold:
                state_match, created = StateMatched.objects.get_or_create(
                    official=official,
                )
                unmatched.status = "MATCHED"
                unmatched.save()
                state_match.matched.add(unmatched)
                state_match.score = score
                state_match.save()
                
                created_count += 1
        
        logging.info(f"Total state matches: {created_count}")
        self.stdout.write(self.style.SUCCESS(f"✓ {created_count} matches criados"))
        
        return matches

    def apply_fuzzy_matched_states(self, name=None):
        """Aplica os matches, atualizando locations para usar estados oficiais"""
        if name:
            states_official = State.objects.filter(name=name, status="OFFICIAL")
        else:
            states_official = State.objects.filter(status="OFFICIAL")
        
        total_locations = 0
        for state in states_official:
            try:
                state_matched = StateMatched.objects.get(official=state)
                locations_count = state_matched.apply_to_locations()
                matched = state_matched.matched.all()
                matched.update(status="PROCESSED")
                total_locations += locations_count
                
                logging.info(
                    f"{state.name}: {locations_count} locations, "
                    f"matched: {list(matched.values_list('name', flat=True))}"
                )
            except StateMatched.DoesNotExist:
                continue
        
        self.stdout.write(self.style.SUCCESS(
            f"✓ {total_locations} locations atualizados"
        ))

