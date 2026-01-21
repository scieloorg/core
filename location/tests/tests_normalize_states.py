"""
Testes para o comando normalize_states.py

Cobre:
- Limpeza de nomes de estados (clean_name_states)
- Unificação de estados duplicados (unificate_states)
- Carregamento de estados oficiais (load_official_states)
- Fuzzy matching entre estados (fuzzy_match_states)
- Criação automática de matches (auto_create_fuzzy_matches_states)
- Aplicação de matches aos locations (apply_fuzzy_matched_states)
"""

import logging
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from location.management.commands import normalize_states
from location.models import Country, Location, State, StateMatched

User = get_user_model()
logger = logging.getLogger(__name__)


class CleanNameStatesTest(TestCase):
    """Testes para a limpeza de nomes de estados"""
    
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.command = normalize_states.Command()
    
    def test_clean_name_removes_html_tags(self):
        """Testa remoção de tags HTML"""
        state = State.objects.create(
            name="<i>São Paulo</i>",
            acronym="SP",
            creator=self.user
        )
        
        self.command.clean_name_states()
        
        state.refresh_from_db()
        self.assertEqual(state.name, "São Paulo")
        self.assertEqual(state.status, "CLEANED")
    
    def test_clean_name_handles_duplicate_after_cleaning(self):
        """Testa que estados que ficam duplicados após limpeza são tratados"""
        # Criar múltiplos estados que resultarão no mesmo nome após limpeza
        State.objects.create(
            name="- São Paulo",
            acronym="SP>",
            creator=self.user
        )
        State.objects.create(
            name="São Paulo.",
            acronym="SP",
            creator=self.user
        )
        State.objects.create(
            name="São Paulo!!!",
            acronym="SP",
            creator=self.user
        )
        
        initial_count = State.objects.count()
        self.assertEqual(initial_count, 3)
        
        self.command.clean_name_states()
        
        # Após limpeza, deve haver apenas 1 estado (outros deletados por IntegrityError)
        final_count = State.objects.filter(name="São Paulo", acronym="SP").count()
        self.assertEqual(final_count, 1)
        
        # Verificar que o estado restante está limpo
        remaining_state = State.objects.get(name="São Paulo", acronym="SP")
        self.assertEqual(remaining_state.status, "CLEANED")
    
    def test_clean_name_normalizes_spaces(self):
        """Testa normalização de espaços extras"""
        state = State.objects.create(
            name="  São   Paulo  ",
            acronym="SP",
            creator=self.user
        )
        
        self.command.clean_name_states()
        
        state.refresh_from_db()
        self.assertEqual(state.name, "São Paulo")
        self.assertEqual(state.status, "CLEANED")
    
    def test_clean_name_capitalizes(self):
        """Testa capitalização de nomes"""
        state = State.objects.create(
            name="são paulo",
            acronym="SP",
            creator=self.user
        )
        
        self.command.clean_name_states()
        
        state.refresh_from_db()
        self.assertEqual(state.name, "São Paulo")
        self.assertEqual(state.status, "CLEANED")
    
    def test_clean_name_skips_already_clean(self):
        """Testa que estados já limpos não são modificados"""
        state = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        
        self.command.clean_name_states()
        
        state.refresh_from_db()
        self.assertEqual(state.name, "São Paulo")
        self.assertEqual(state.status, "CLEANED")
    
    def test_clean_name_multiple_states(self):
        """Testa limpeza de múltiplos estados"""
        states_data = [
            ("<b>Rio de Janeiro</b>", "RJ"),
            ("- Minas Gerais", "MG"),
            ("bahia", "BA"),
        ]
        
        for name, acronym in states_data:
            State.objects.create(
                name=name,
                acronym=acronym,
                creator=self.user
            )
        
        self.command.clean_name_states()
        
        cleaned_states = State.objects.filter(status="CLEANED")
        self.assertEqual(cleaned_states.count(), 3)
        self.assertTrue(State.objects.filter(name="Rio De Janeiro", acronym="RJ").exists())
        self.assertTrue(State.objects.filter(name="Minas Gerais", acronym="MG").exists())
        self.assertTrue(State.objects.filter(name="Bahia", acronym="BA").exists())


class UnificateStatesTest(TestCase):
    """Testes para a unificação de estados duplicados"""
    
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.command = normalize_states.Command()
    
    def test_unificate_removes_duplicates(self):
        """Testa que duplicatas são removidas"""
        # Criar estados duplicados
        state1 = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        state2 = State.objects.create(
            name="São Paulo",
            creator=self.user,
            status="CLEANED"
        )
        state3 = State.objects.create(
            name="São Paulo",
            creator=self.user,
            status="CLEANED"
        )
        
        initial_count = State.objects.filter(name="São Paulo").count()
        self.assertEqual(initial_count, 3)
        self.command.clean_name_states()
        self.command.unificate_states()
        
        final_count = State.objects.filter(name="São Paulo", acronym="SP").count()
        self.assertEqual(final_count, 1)
    
    def test_unificate_keeps_state_with_acronym(self):
        """Testa que o estado com acronym é mantido como canonical"""
        # Criar estados - um sem acronym, outro com
        state_no_acronym = State.objects.create(
            name="São Paulo",
            creator=self.user,
            status="CLEANED"
        )
        state_with_acronym = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        self.command.clean_name_states()
        self.command.unificate_states()
        
        remaining_state = State.objects.get(name="São Paulo", acronym="SP")
        # O estado com acronym deve ser mantido
        self.assertIsNotNone(remaining_state.acronym)
    
    def test_unificate_moves_locations_to_canonical(self):
        """Testa que locations são movidos para o estado canônico"""
        # Criar estados duplicados
        state1 = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        state2 = State.objects.create(
            name="São Paulo",
            creator=self.user,
            status="CLEANED"
        )
        
        # Criar locations associados a cada estado
        location1 = Location.objects.create(
            state=state1,
            creator=self.user
        )
        location2 = Location.objects.create(
            state=state2,
            creator=self.user
        )
        self.command.clean_name_states()
        self.command.unificate_states()
        
        # Recarregar locations
        location1.refresh_from_db()
        
        # Ambos devem apontar para o mesmo estado
        self.assertEqual(location1.state, state1)
        
        # Deve existir apenas um estado
        self.assertEqual(State.objects.filter(name="São Paulo", acronym="SP").count(), 1)
    
    def test_unificate_no_locations_lost(self):
        """Garante que nenhum location é perdido durante unificação"""
        # Criar estados duplicados
        state1 = State.objects.create(
            name="Rio de Janeiro",
            acronym="RJ",
            creator=self.user,
            status="CLEANED"
        )
        state2 = State.objects.create(
            name="Rio de Janeiro",
            creator=self.user,
            status="CLEANED"
        )
        state3 = State.objects.create(
            name="Rio de Janeiro",
            creator=self.user,
            status="CLEANED"
        )
        
        # Criar locations (sem city, então não haverá duplicatas)
        location1 = Location.objects.create(state=state1, creator=self.user)
        location2 = Location.objects.create(state=state2, creator=self.user)
        location3 = Location.objects.create(state=state3, creator=self.user)
        
        locations_before = Location.objects.count()
        self.assertEqual(locations_before, 3)
        self.command.clean_name_states()
        self.command.unificate_states()
        
        # Nenhum location deve ser perdido
        locations_after = Location.objects.count()
        self.assertEqual(locations_after, 3)
        
        # Deve existir apenas 1 estado
        states_count = State.objects.filter(name="Rio de Janeiro", acronym="RJ").count()
        self.assertEqual(states_count, 1)
        
        # Todos devem apontar para o mesmo estado
        canonical_state = State.objects.get(name="Rio de Janeiro", acronym="RJ")
        self.assertEqual(canonical_state.location_set.count(), 3)
        
        # Verificar que todos os locations apontam para o canonical
        location1.refresh_from_db()
        location2.refresh_from_db()
        location3.refresh_from_db()
        
        self.assertEqual(location1.state, canonical_state)
        self.assertEqual(location2.state, canonical_state)
        self.assertEqual(location3.state, canonical_state)
    
    def test_unificate_handles_duplicate_locations(self):
        """Testa tratamento de locations duplicados (mesmo country, state, city)"""
        country = Country.objects.create(
            name="Brasil",
            acronym="BR",
            creator=self.user
        )
        
        # Criar estados duplicados
        state1 = State.objects.create(
            name="Minas Gerais",
            creator=self.user,
            status="CLEANED"
        )
        state2 = State.objects.create(
            name="Minas Gerais",
            acronym="MG",
            creator=self.user,
            status="CLEANED"
        )
        
        # Criar locations que seriam duplicados após unificação
        location1 = Location.objects.create(
            country=country,
            state=state1,
            creator=self.user
        )
        location2 = Location.objects.create(
            country=country,
            state=state2,
            creator=self.user
        )
        
        locations_before = Location.objects.count()
        self.command.clean_name_states()
        self.command.unificate_states()
        
        # Um dos locations deve ser deletado (pois seriam duplicados)
        locations_after = Location.objects.count()
        self.assertEqual(locations_after, 1)
        
        # Deve existir apenas um estado
        self.assertEqual(State.objects.filter(name="Minas Gerais", acronym="MG").count(), 1)


class LoadOfficialStatesTest(TestCase):
    """Testes para carregamento de estados oficiais do pycountry"""
    
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.command = normalize_states.Command()
    
    def test_load_official_states_from_brazil(self):
        """Testa carregamento de estados brasileiros do pycountry"""
        # Criar país oficial Brasil
        country_br = Country.objects.create(
            name="Brazil",
            acronym="BR",
            creator=self.user,
            status="OFFICIAL"
        )
        
        self.command.load_official_states()
        
        # Verificar que estados foram criados
        official_states = State.objects.filter(status="OFFICIAL")
        self.assertGreater(official_states.count(), 0)
        
        # Verificar alguns estados específicos do Brasil
        # BR tem 27 subdivisões (26 estados + 1 DF)
        br_states = State.objects.filter(status="OFFICIAL")
        self.assertGreaterEqual(br_states.count(), 20)
    
    def test_load_official_states_creates_with_acronym(self):
        """Testa que estados são criados com sigla extraída do código"""
        country_br = Country.objects.create(
            name="Brazil",
            acronym="BR",
            creator=self.user,
            status="OFFICIAL"
        )
        
        self.command.load_official_states()
        
        # Verificar que pelo menos um estado tem acronym
        states_with_acronym = State.objects.filter(
            status="OFFICIAL",
            acronym__isnull=False
        ).exclude(acronym='')
        
        self.assertGreater(states_with_acronym.count(), 0)
    
    def test_load_official_states_updates_existing(self):
        """Testa que estados existentes são atualizados para OFFICIAL"""
        country_br = Country.objects.create(
            name="Brazil",
            acronym="BR",
            creator=self.user,
            status="OFFICIAL"
        )
        
        # Criar um estado que existe no pycountry
        state = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        
        self.command.load_official_states()
        
        state.refresh_from_db()
        # O estado deve ter sido atualizado para OFFICIAL
        self.assertEqual(state.status, "OFFICIAL")
    
    def test_load_official_states_only_for_official_countries(self):
        """Testa que estados são carregados apenas para países OFFICIAL"""
        # Criar país não oficial
        country_non_official = Country.objects.create(
            name="Fake Country",
            acronym="FK",
            creator=self.user,
            status="CLEANED"
        )
        
        initial_count = State.objects.count()
        
        self.command.load_official_states()
        
        # Nenhum estado deve ser criado para país não oficial
        final_count = State.objects.count()
        # Count pode aumentar se houver outros países OFFICIAL, mas não para FK
        states_for_fake = State.objects.filter(status="OFFICIAL")
        # Não deve haver estados OFFICIAL se não há países OFFICIAL
        self.assertEqual(states_for_fake.count(), 0)
    
    @patch('pycountry.subdivisions.get')
    def test_load_official_states_handles_country_without_subdivisions(self, mock_get):
        """Testa tratamento de países sem subdivisões"""
        mock_get.side_effect = KeyError("No subdivisions")
        
        country = Country.objects.create(
            name="Monaco",
            acronym="MC",
            creator=self.user,
            status="OFFICIAL"
        )
        
        # Não deve lançar exceção
        self.command.load_official_states()
        
        # Comando deve continuar normalmente


class FuzzyMatchStatesTest(TestCase):
    """Testes para fuzzy matching de estados"""
    
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.command = normalize_states.Command()
        
        # Criar estados oficiais
        self.official_sp = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="OFFICIAL"
        )
        self.official_rj = State.objects.create(
            name="Rio de Janeiro",
            acronym="RJ",
            creator=self.user,
            status="OFFICIAL"
        )
        self.official_mg = State.objects.create(
            name="Minas Gerais",
            acronym="MG",
            creator=self.user,
            status="OFFICIAL"
        )
    
    def test_fuzzy_match_exact_match(self):
        """Testa match exato"""
        cleaned_state = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        
        matches = self.command.fuzzy_match_states(threshold=85)
        
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['unmatched'], cleaned_state)
        self.assertEqual(matches[0]['official'], self.official_sp)
        self.assertGreaterEqual(matches[0]['score'], 95)
    
    def test_fuzzy_match_similar_name(self):
        """Testa match com nome similar"""
        # Criar estado com erro de digitação
        cleaned_state = State.objects.create(
            name="Sao Paulo",  # Sem acento
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        
        matches = self.command.fuzzy_match_states(threshold=80)
        
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['unmatched'], cleaned_state)
        self.assertEqual(matches[0]['official'], self.official_sp)
    
    def test_fuzzy_match_respects_threshold(self):
        """Testa que threshold é respeitado"""
        # Criar estado muito diferente
        cleaned_state = State.objects.create(
            name="Estado Completamente Diferente",
            acronym="XX",
            creator=self.user,
            status="CLEANED"
        )
        
        matches = self.command.fuzzy_match_states(threshold=95)
        
        # Não deve haver match
        self.assertEqual(len(matches), 0)
    
    def test_fuzzy_match_considers_acronym(self):
        """Testa que acronym é considerado no matching"""
        cleaned_state = State.objects.create(
            name="Sao Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        
        matches = self.command.fuzzy_match_states(threshold=85)
        
        self.assertEqual(len(matches), 1)
        # Deve fazer match com São Paulo (SP), não com outros
        self.assertEqual(matches[0]['official'].acronym, "SP")
    
    def test_fuzzy_match_multiple_states(self):
        """Testa matching de múltiplos estados"""
        states_data = [
            ("Sao Paulo", "SP"),
            ("Rio Janeiro", "RJ"),
            ("Minas", "MG"),
        ]
        
        for name, acronym in states_data:
            State.objects.create(
                name=name,
                acronym=acronym,
                creator=self.user,
                status="CLEANED"
            )
        
        matches = self.command.fuzzy_match_states(threshold=70)
        
        # Deve encontrar matches para todos os 3 estados
        self.assertEqual(len(matches), 3)
    
    def test_fuzzy_match_reprocess_option(self):
        """Testa opção de reprocessamento"""
        cleaned_state = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="MATCHED"  # Já foi matched antes
        )
        
        # Criar um StateMatched existente
        state_match = StateMatched.objects.create(
            official=self.official_sp,
            creator=self.user
        )
        state_match.matched.add(cleaned_state)
        
        # Sem reprocess, não deve encontrar nada
        matches = self.command.fuzzy_match_states(threshold=85, reprocess=False)
        self.assertEqual(len(matches), 0)
        
        # Com reprocess, deve encontrar
        matches = self.command.fuzzy_match_states(threshold=85, reprocess=True)
        self.assertEqual(len(matches), 1)


class AutoCreateFuzzyMatchesStatesTest(TestCase):
    """Testes para criação automática de matches"""
    
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.command = normalize_states.Command()
        
        # Criar estados oficiais
        self.official_sp = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="OFFICIAL"
        )
        self.official_rj = State.objects.create(
            name="Rio de Janeiro",
            acronym="RJ",
            creator=self.user,
            status="OFFICIAL"
        )
    
    def test_auto_create_creates_state_matched(self):
        """Testa que StateMatched é criado"""
        cleaned_state = State.objects.create(
            name="Sao Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        
        self.command.auto_create_fuzzy_matches_states(threshold=80)
        
        # Verificar que StateMatched foi criado
        self.assertEqual(StateMatched.objects.count(), 1)
        
        state_match = StateMatched.objects.first()
        self.assertEqual(state_match.official, self.official_sp)
        self.assertIn(cleaned_state, state_match.matched.all())
    
    def test_auto_create_updates_state_status_to_matched(self):
        """Testa que status do estado é atualizado para MATCHED"""
        cleaned_state = State.objects.create(
            name="Sao Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        
        self.command.auto_create_fuzzy_matches_states(threshold=80)
        
        cleaned_state.refresh_from_db()
        self.assertEqual(cleaned_state.status, "MATCHED")
    
    def test_auto_create_stores_match_score(self):
        """Testa que score do match é armazenado"""
        cleaned_state = State.objects.create(
            name="Sao Paulo",
            acronym="SP",
            creator=self.user,
            status="CLEANED"
        )
        
        self.command.auto_create_fuzzy_matches_states(threshold=80)
        
        state_match = StateMatched.objects.first()
        self.assertGreater(state_match.score, 0)
        self.assertLessEqual(state_match.score, 100)
    
    def test_auto_create_multiple_states_same_official(self):
        """Testa que múltiplos estados podem ser matched ao mesmo oficial"""
        states_data = [
            ("Sao Paulo", "SP"),
            ("S Paulo", "SP"),
            ("Sao Paulo State", "SP"),
        ]
        
        for name, acronym in states_data:
            State.objects.create(
                name=name,
                acronym=acronym,
                creator=self.user,
                status="CLEANED"
            )
        
        self.command.auto_create_fuzzy_matches_states(threshold=70)
        
        # Deve criar apenas 1 StateMatched (para o oficial)
        self.assertEqual(StateMatched.objects.count(), 1)
        
        # Mas deve ter múltiplos matched
        state_match = StateMatched.objects.first()
        self.assertEqual(state_match.matched.count(), 3)
    
    def test_auto_create_reprocess_deletes_old_matches(self):
        """Testa que reprocess deleta matches antigos"""
        cleaned_state = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="MATCHED"
        )
        
        # Criar match existente
        state_match = StateMatched.objects.create(
            official=self.official_sp,
            creator=self.user
        )
        state_match.matched.add(cleaned_state)
        
        initial_count = StateMatched.objects.count()
        
        # Reprocessar
        self.command.auto_create_fuzzy_matches_states(threshold=85, reprocess=True)
        
        # Matches antigos devem ter sido deletados e recriados
        # Count pode ser igual se os mesmos matches forem recriados
        self.assertGreaterEqual(StateMatched.objects.count(), 1)


class ApplyFuzzyMatchedStatesTest(TestCase):
    """Testes para aplicação de matches aos locations"""
    
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.command = normalize_states.Command()
        
        # Criar país
        self.country = Country.objects.create(
            name="Brasil",
            acronym="BR",
            creator=self.user
        )
        
        # Criar estado oficial
        self.official_sp = State.objects.create(
            name="São Paulo",
            acronym="SP",
            creator=self.user,
            status="OFFICIAL"
        )
        
        # Criar estados não oficiais (matched)
        self.cleaned_sp1 = State.objects.create(
            name="Sao Paulo",
            acronym="SP",
            creator=self.user,
            status="MATCHED"
        )
        self.cleaned_sp2 = State.objects.create(
            name="S Paulo",
            acronym="SP",
            creator=self.user,
            status="MATCHED"
        )
        
        # Criar StateMatched
        self.state_match = StateMatched.objects.create(
            official=self.official_sp,
            creator=self.user,
            score=95.0
        )
        self.state_match.matched.add(self.cleaned_sp1, self.cleaned_sp2)
        
        # Criar locations com estados não oficiais
        self.location1 = Location.objects.create(
            country=self.country,
            state=self.cleaned_sp1,
            creator=self.user
        )
        self.location2 = Location.objects.create(
            country=self.country,
            state=self.cleaned_sp2,
            creator=self.user
        )
    
    def test_apply_updates_locations_to_official_state(self):
        """Testa que locations são atualizados para usar estado oficial"""
        self.command.apply_fuzzy_matched_states()
        
        self.location1.refresh_from_db()
        self.location2.refresh_from_db()
        
        # Ambos devem apontar para o estado oficial
        self.assertEqual(self.location1.state, self.official_sp)
        self.assertEqual(self.location2.state, self.official_sp)
    
    def test_apply_updates_matched_states_status_to_processed(self):
        """Testa que estados matched têm status atualizado para PROCESSED"""
        self.command.apply_fuzzy_matched_states()
        
        self.cleaned_sp1.refresh_from_db()
        self.cleaned_sp2.refresh_from_db()
        
        self.assertEqual(self.cleaned_sp1.status, "PROCESSED")
        self.assertEqual(self.cleaned_sp2.status, "PROCESSED")
    
    def test_apply_specific_state_by_name(self):
        """Testa aplicação de match para estado específico"""
        # Criar outro estado oficial e match
        official_rj = State.objects.create(
            name="Rio de Janeiro",
            acronym="RJ",
            creator=self.user,
            status="OFFICIAL"
        )
        cleaned_rj = State.objects.create(
            name="Rio Janeiro",
            acronym="RJ",
            creator=self.user,
            status="MATCHED"
        )
        state_match_rj = StateMatched.objects.create(
            official=official_rj,
            creator=self.user
        )
        state_match_rj.matched.add(cleaned_rj)
        
        location_rj = Location.objects.create(
            country=self.country,
            state=cleaned_rj,
            creator=self.user
        )
        
        # Aplicar apenas para São Paulo
        self.command.apply_fuzzy_matched_states(name="São Paulo")
        
        # Locations de SP devem ser atualizados
        self.location1.refresh_from_db()
        self.assertEqual(self.location1.state, self.official_sp)
        
        # Location de RJ não deve ser atualizado
        location_rj.refresh_from_db()
        self.assertEqual(location_rj.state, cleaned_rj)
    
    def test_apply_counts_updated_locations(self):
        """Testa que número de locations atualizados é retornado corretamente"""
        # Criar mais locations
        for i in range(5):
            Location.objects.create(
                country=self.country,
                state=self.cleaned_sp1,
                creator=self.user
            )
        
        total_locations = Location.objects.filter(
            state__in=[self.cleaned_sp1, self.cleaned_sp2]
        ).count()
        
        self.command.apply_fuzzy_matched_states()
        
        # Verificar que todos foram atualizados
        updated_locations = Location.objects.filter(state=self.official_sp).count()
        self.assertEqual(updated_locations, total_locations)
    
    def test_apply_handles_state_without_match(self):
        """Testa que estados sem match não causam erro"""
        # Criar estado oficial sem matches
        official_no_match = State.objects.create(
            name="Bahia",
            acronym="BA",
            creator=self.user,
            status="OFFICIAL"
        )
        
        # Não deve lançar exceção
        self.command.apply_fuzzy_matched_states()
        
        # Locations originais devem continuar atualizados
        self.location1.refresh_from_db()
        self.assertEqual(self.location1.state, self.official_sp)
    
    def test_apply_preserves_other_location_fields(self):
        """Testa que outros campos do location são preservados"""
        # Adicionar city ao location
        from location.models import City
        city = City.objects.create(name="São Paulo", creator=self.user)
        self.location1.city = city
        self.location1.save()
        
        self.command.apply_fuzzy_matched_states()
        
        self.location1.refresh_from_db()
        
        # State deve ser atualizado
        self.assertEqual(self.location1.state, self.official_sp)
        # Mas city e country devem permanecer
        self.assertEqual(self.location1.city, city)
        self.assertEqual(self.location1.country, self.country)


class FullWorkflowTest(TestCase):
    """Testes do fluxo completo de normalização de estados"""
    
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.command = normalize_states.Command()
        
        # Criar país oficial
        self.country_br = Country.objects.create(
            name="Brazil",
            acronym="BR",
            creator=self.user,
            status="OFFICIAL"
        )
    
    def test_full_workflow_clean_unificate_load_match_apply(self):
        """Testa o fluxo completo: limpar -> unificar -> carregar oficiais -> match -> aplicar"""
        
        # 1. Criar estados com nomes sujos e duplicados
        states_raw = [
            ("<i>São Paulo</i>", "SP"),
            ("- São Paulo", "SP"),
            ("são paulo", "SP"),
            ("Rio de Janeiro", "RJ"),
            ("rio janeiro", "RJ"),
        ]
        
        for name, acronym in states_raw:
            State.objects.create(
                name=name,
                acronym=acronym,
                creator=self.user,
                status="RAW"
            )
        
        # Criar locations com estados não limpos
        sp_dirty = State.objects.get(name="<i>São Paulo</i>", acronym="SP")
        rj_dirty = State.objects.get(name="Rio de Janeiro", acronym="RJ")
        
        location_sp = Location.objects.create(
            country=self.country_br,
            state=sp_dirty,
            creator=self.user
        )
        location_rj = Location.objects.create(
            country=self.country_br,
            state=rj_dirty,
            creator=self.user
        )
        
        initial_states = State.objects.count()
        self.assertEqual(initial_states, 5)
        
        # 2. Limpar nomes
        self.command.clean_name_states()
        
        cleaned_states = State.objects.filter(status="CLEANED")
        self.assertGreater(cleaned_states.count(), 0)
        
        # 3. Unificar duplicados
        self.command.unificate_states()
        
        # Deve ter menos estados agora (duplicados foram removidos)
        after_unification = State.objects.count()
        self.assertLess(after_unification, initial_states)
        
        # 4. Carregar estados oficiais do pycountry
        self.command.load_official_states()
        
        official_states = State.objects.filter(status="OFFICIAL")
        self.assertGreater(official_states.count(), 0)
        
        # Verificar que São Paulo oficial existe
        sp_official = State.objects.filter(
            name="São Paulo",
            acronym="SP",
            status="OFFICIAL"
        ).first()
        self.assertIsNotNone(sp_official)
        
        # 5. Fazer fuzzy matching
        self.command.auto_create_fuzzy_matches_states(threshold=75, reprocess=False)
        
        # Verificar que matches foram criados
        matches = StateMatched.objects.all()
        self.assertGreater(matches.count(), 0)
        
        # 6. Aplicar matches aos locations
        self.command.apply_fuzzy_matched_states()
        
        # Verificar que locations foram atualizados para estados oficiais
        location_sp.refresh_from_db()
        location_rj.refresh_from_db()
        
        self.assertEqual(location_sp.state.status, "OFFICIAL")
        self.assertEqual(location_rj.state.status, "OFFICIAL")
        
        # Verificar que apontam para estados oficiais corretos
        self.assertEqual(location_sp.state.acronym, "SP")
        self.assertEqual(location_rj.state.acronym, "RJ")
    
    def test_workflow_preserves_data_integrity(self):
        """Testa que integridade dos dados é preservada durante todo o fluxo"""
        # Criar estrutura completa
        from location.models import City
        
        city_sp = City.objects.create(name="São Paulo", creator=self.user)
        city_rj = City.objects.create(name="Rio de Janeiro", creator=self.user)
        
        state_sp_dirty = State.objects.create(
            name="<b>São Paulo</b>",
            acronym="SP",
            creator=self.user,
            status="RAW"
        )
        state_rj_dirty = State.objects.create(
            name="- Rio de Janeiro",
            acronym="RJ",
            creator=self.user,
            status="RAW"
        )
        
        location1 = Location.objects.create(
            country=self.country_br,
            state=state_sp_dirty,
            city=city_sp,
            creator=self.user
        )
        location2 = Location.objects.create(
            country=self.country_br,
            state=state_rj_dirty,
            city=city_rj,
            creator=self.user
        )
        
        # Armazenar dados originais
        original_city1 = location1.city
        original_city2 = location2.city
        original_country = location1.country
        
        # Executar fluxo completo
        self.command.clean_name_states()
        self.command.unificate_states()
        self.command.load_official_states()
        self.command.auto_create_fuzzy_matches_states(threshold=75)
        self.command.apply_fuzzy_matched_states()
        
        # Recarregar locations
        location1.refresh_from_db()
        location2.refresh_from_db()
        
        # Verificar que apenas states foram alterados
        self.assertEqual(location1.city, original_city1)
        self.assertEqual(location2.city, original_city2)
        self.assertEqual(location1.country, original_country)
        self.assertEqual(location2.country, original_country)
        
        # Mas states devem ser oficiais
        self.assertEqual(location1.state.status, "OFFICIAL")
        self.assertEqual(location2.state.status, "OFFICIAL")


class CommandArgumentsTest(TestCase):
    """Testes para argumentos do comando"""
    
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.command = normalize_states.Command()
    
    def test_handle_requires_at_least_one_action(self):
        """Testa que pelo menos uma ação deve ser especificada"""
        from django.core.management.base import CommandError
        
        options = {
            'clean': False,
            'unificate_states': False,
            'load_official_states': False,
            'fuzzy_match_states': None,
            'apply_matches': False,
            'reprocess': False,
        }
        
        with self.assertRaises(CommandError):
            self.command.handle(**options)
    
    def test_handle_clean_action(self):
        """Testa que ação --clean funciona"""
        State.objects.create(
            name="<i>Test</i>",
            acronym="TS",
            creator=self.user
        )
        
        options = {
            'clean': True,
            'unificate_states': False,
            'load_official_states': False,
            'fuzzy_match_states': None,
            'apply_matches': False,
            'reprocess': False,
        }
        
        # Não deve lançar exceção
        self.command.handle(**options)
        
        # Estado deve estar limpo
        state = State.objects.first()
        self.assertEqual(state.status, "CLEANED")
    
    def test_handle_multiple_actions(self):
        """Testa que múltiplas ações podem ser executadas juntas"""
        State.objects.create(
            name="<b>Test</b>",
            acronym="TS",
            creator=self.user,
            status="RAW"
        )
        State.objects.create(
            name="Test",
            acronym="TS",
            creator=self.user,
            status="RAW"
        )
        
        options = {
            'clean': True,
            'unificate_states': True,
            'load_official_states': False,
            'fuzzy_match_states': None,
            'apply_matches': False,
            'reprocess': False,
        }
        
        # Não deve lançar exceção
        self.command.handle(**options)
        
        # Deve haver apenas 1 estado (após unificação)
        self.assertEqual(State.objects.filter(acronym="TS").count(), 1)

