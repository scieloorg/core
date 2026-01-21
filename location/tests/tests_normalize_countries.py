import logging
from unittest.mock import patch

import pycountry
from django.contrib.auth import get_user_model
from django.test import TestCase

from location import models
from location.management.commands import normalize_countries

User = get_user_model()
logger = logging.getLogger(__name__)

class NormalizeLocationsTest(TestCase):
    """
    Testa a normalização e unificação de países duplicados.
    
    Simula o cenário real onde existem múltiplas variações do nome de um país
    (com caracteres especiais, espaços, etc.) que devem ser normalizadas e
    consolidadas em um único registro.
    """
    
    def setUp(self) -> None:
        """Configura o ambiente de teste com países duplicados e locations"""
        self.name = '<i>Brasil</i>'
        self.user, _ = User.objects.get_or_create(username="test_user")
        
        # Criar países duplicados com variações de "Brasil"
        # Simulando dados reais que podem vir de diferentes fontes
        self.country1 = models.Country.objects.create(
            name="Brasile",  # Erro de digitação
            creator=self.user
        )
        
        self.country2 = models.Country.objects.create(
            name="Brasil",
            acronym="IO",
            creator=self.user
        )
        
        self.country3 = models.Country.objects.create(
            name="- BRASIL",  # Com prefixo e maiúsculas
            creator=self.user
        )
        
        self.country4 = models.Country.objects.create(
            name="Brasil",
            acronym="BV",
            creator=self.user
        )
        
        self.country5 = models.Country.objects.create(
            name=", Brasil",  # Com vírgula no início
            creator=self.user
        )
        
        self.country6 = models.Country.objects.create(
            name="Brasill",  # Erro de digitação (duplo 'l')
            creator=self.user
        )
        
        self.country7 = models.Country.objects.create(
            name="Brasil.",  # Com ponto final
            creator=self.user
        )
        
        self.country8 = models.Country.objects.create(
            name="Brasil",
            acronym="BM",
            creator=self.user
        )
        
        self.country9 = models.Country.objects.create(
            name="- Brasil",  # Com prefixo
            creator=self.user
        )
        
        self.country10 = models.Country.objects.create(
            name="Brasil",
            acronym="BT",
            acron3="BTN",
            creator=self.user
        )
        
        self.country11 = models.Country.objects.create(
            name="Brasil",
            acronym="AF",
            acron3="AFG",
            creator=self.user
        )
        
        # Criar locations associados a diferentes países duplicados
        self.location1 = models.Location.objects.create(
            country=self.country1,  # Brasile
            creator=self.user,
        )
        self.location2 = models.Location.objects.create(
            country=self.country2,  # Brasil (IO)
            creator=self.user
        )
        self.location3 = models.Location.objects.create(
            country=self.country3,  # - BRASIL
            creator=self.user
        )
        self.location4 = models.Location.objects.create(
            country=self.country9,  # - Brasil
            creator=self.user
        )
        
        # Armazenar IDs originais para verificação posterior
        self.original_country_ids = [
            self.country1.id, self.country2.id, self.country3.id, 
            self.country4.id, self.country5.id, self.country6.id,
            self.country7.id, self.country8.id, self.country9.id,
            self.country10.id, self.country11.id
        ]

    def test_clean_country_name(self):
        """Testa a normalização de nomes com diferentes variações"""
        test_cases = [
            ("- BRASIL", "Brasil"),
            ("- Brasil", "Brasil"),
            ("Brasil.", "Brasil"),
            (" BRASIL", "Brasil"),
            (" BRASIL ", "Brasil"),
            (", Brasil", "Brasil"),
            ("BRASIL!!!", "Brasil"),
            ("  Brasil  ", "Brasil"),
        ]

        for input_name, expected_output in test_cases:
            with self.subTest(input=input_name):
                self.assertEqual(normalize_countries.clean_country_name(input_name), expected_output)

    def test_clean_model_country_name(self):
        """Testa a normalização de todos os países no banco"""
        # Verificar estado inicial
        self.assertEqual(self.country1.name, "Brasile")
        self.assertEqual(self.country3.name, "- BRASIL")
        self.assertEqual(self.country7.name, "Brasil.")
        
        # Normalizar
        normalize_countries.Command().clean_name_countries()
        
        # Recarregar e verificar
        self.country1.refresh_from_db()
        self.country3.refresh_from_db()
        self.country7.refresh_from_db()
        
        self.assertEqual(self.country1.name, "Brasile")
        self.assertEqual(self.country3.name, "Brasil")
        self.assertEqual(self.country7.name, "Brasil")
        
        # Verificar que o status foi atualizado
        self.assertEqual(self.country1.status, "CLEANED")
        self.assertEqual(self.country3.status, "CLEANED")

    def test_unificate_country_full_workflow(self):
        """Testa o fluxo completo de normalização e unificação"""
        # 1. Estado inicial: múltiplos países com nomes diferentes
        initial_count = models.Country.objects.count()
        self.assertEqual(initial_count, 11)
        
        # 2. Normalizar nomes
        normalize_countries.Command().clean_name_countries()
        
        # Verificar que todos foram normalizados para "Brasil"
        brasil_count = models.Country.objects.filter(name="Brasil").count()
        self.assertEqual(brasil_count, 9)
        
        # Mas ainda são registros separados
        self.assertEqual(models.Country.objects.count(), 11)
        
        # 3. Unificar países duplicados
        normalize_countries.Command().unificate_countries()
        
        # 4. Verificações após unificação
        # Deve existir apenas 1 país "Brasil"
        final_count = models.Country.objects.filter(name__exact="Brasil").count()
        self.assertEqual(final_count, 1)
        
        # Total de países deve ser 3
        # ['Brasile', 'Brasil', 'Brasill']
        self.assertEqual(models.Country.objects.count(), 3)
        
        # 5. Verificar que todos os locations apontam para o mesmo país
        self.location1.refresh_from_db()
        self.location2.refresh_from_db()
        self.location3.refresh_from_db()
        self.location4.refresh_from_db()
        
        canonical_country = models.Country.objects.get(name="Brasil")
        
        # Todos devem apontar para o mesmo país
        self.assertEqual(self.location2.country, canonical_country)
        self.assertEqual(self.location3.country, canonical_country)
        self.assertEqual(self.location4.country, canonical_country)
        
        # Verificar por ID também
        self.assertEqual(self.location2.country.id, canonical_country.id)
        self.assertEqual(self.location3.country.id, canonical_country.id)
        self.assertEqual(self.location4.country.id, canonical_country.id)
        
        # O país canonical deve ter todos os 3 locations
        self.assertEqual(canonical_country.location_set.count(), 3)

    def test_locations_point_to_same_country_after_unification(self):
        """Testa especificamente que location2 e location3 apontam para o mesmo país"""
        # Normalizar e unificar
        normalize_countries.Command().clean_name_countries()
        normalize_countries.Command().unificate_countries()
        
        # Recarregar locations
        self.location2.refresh_from_db()
        self.location3.refresh_from_db()
        self.location4.refresh_from_db()
        
        # Verificar que são o mesmo objeto (mesmo ID)
        self.assertEqual(self.location2.country, self.location3.country)
        self.assertEqual(self.location2.country.id, self.location3.country.id)
        
        # Verificar com location4 também
        self.assertEqual(self.location2.country, self.location4.country)
        self.assertEqual(self.location3.country, self.location4.country)
        
        # Todos devem ter o mesmo nome normalizado
        self.assertEqual(self.location2.country.name, "Brasil")
        self.assertEqual(self.location3.country.name, "Brasil")
        self.assertEqual(self.location4.country.name, "Brasil")

    def test_no_locations_lost_during_unification(self):
        """Garante que nenhum location é perdido durante a unificação"""
        # Contar locations antes
        locations_before = models.Location.objects.count()
        
        # Normalizar e unificar
        normalize_countries.Command().clean_name_countries()
        normalize_countries.Command().unificate_countries()
        
        # Contar locations depois
        locations_after = models.Location.objects.count()
        
        # Nenhum location deve ser perdido
        self.assertEqual(locations_before, locations_after)
        
        # Todos os locations devem ter um país associado
        locations_without_country = models.Location.objects.filter(country__isnull=True).count()
        self.assertEqual(locations_without_country, 0)

    def test_canonical_country_preserves_acronyms(self):
        """Verifica se o país canonical preserva os acrônimos"""
        normalize_countries.Command().clean_name_countries()
        normalize_countries.Command().unificate_countries()
        
        canonical = models.Country.objects.get(name="Brasil")
        
        # Deve ter pelo menos um acrônimo (de algum dos países originais)
        # O canonical escolhido deve ser um que tinha acrônimos
        self.assertTrue(
            canonical.acronym is not None or canonical.acron3 is not None,
            "País canonical deveria preservar acrônimos"
        )


class VerifiedCountriesInDatabaseTest(TestCase):
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.country1 = models.Country.objects.create(
            name="Brazil",
            acronym="BR",
            creator=self.user
        )
        self.country2 = models.Country.objects.create(
            name="Colombia",
            acronym="CO",
            creator=self.user
        )
        self.country3 = models.Country.objects.create(
            name="United States",
            acronym="US",
            creator=self.user
        )

    def test_verified_countries_with_pycountry(self):
        normalize_countries.Command().process_verified_countries()
        self.country1.refresh_from_db()
        self.country2.refresh_from_db()
        self.country3.refresh_from_db()
        self.assertEqual(models.Country.objects.all().count(), len(pycountry.countries))
        self.assertEqual(self.country1.status, "OFFICIAL")
        self.assertEqual(self.country2.status, "OFFICIAL")
        self.assertEqual(self.country3.status, "OFFICIAL")


class ProcessMatchedCountriesTest(TestCase):
    def setUp(self) -> None:
        """Configura o ambiente de teste com países duplicados e locations"""
        self.user, _ = User.objects.get_or_create(username="test_user")
        self.country1 = models.Country.objects.create(
            name="Brasile",  # Erro de digitação
            creator=self.user
        )
        
        self.country2 = models.Country.objects.create(
            name="Brasil",
            acronym="IO",
            creator=self.user
        )
        
        self.country3 = models.Country.objects.create(
            name="- BRASIL",  # Com prefixo e maiúsculas
            creator=self.user
        )
        
        self.country4 = models.Country.objects.create(
            name="Brasil",
            acronym="BV",
            creator=self.user
        )
        
        self.country5 = models.Country.objects.create(
            name=", Brasil",  # Com vírgula no início
            creator=self.user
        )
        
        self.country6 = models.Country.objects.create(
            name="Brasill",  # Erro de digitação (duplo 'l')
            creator=self.user
        )
        
        self.country7 = models.Country.objects.create(
            name="Brasil.",  # Com ponto final
            creator=self.user
        )
        
        self.country8 = models.Country.objects.create(
            name="Brasil",
            acronym="BM",
            creator=self.user
        )
        
        self.country9 = models.Country.objects.create(
            name="- Brasil",  # Com prefixo
            creator=self.user
        )
        
        self.country10 = models.Country.objects.create(
            name="Brasil",
            acronym="BT",
            acron3="BTN",
            creator=self.user
        )
        
        self.country11 = models.Country.objects.create(
            name="Brasil",
            acronym="AF",
            acron3="AFG",
            creator=self.user
        )
        self.country11 = models.Country.objects.create(
            name="teste@gmail.com",
            creator=self.user
        )
        self.location1 = models.Location.objects.create(
            country=self.country1,  # Brasile
            creator=self.user,
        )
        self.location2 = models.Location.objects.create(
            country=self.country2,  # Brasil (IO)
            creator=self.user
        )
        self.location3 = models.Location.objects.create(
            country=self.country3,  # - BRASIL
            creator=self.user
        )        
        normalize_countries.Command().clean_name_countries() # primeiro limpar os nomes, remove acento, spaco, pontuacao
        normalize_countries.Command().unificate_countries() # Remove duplicidade de nomes de paises. ['Brasile', 'Brasil', 'Brasill']
        normalize_countries.Command().process_verified_countries() # Carrega nomes officiais de países em ingles

    def test_matched_countries(self):
        matches = normalize_countries.Command().auto_create_fuzzy_matches(threshold=70)
        country_matched =  models.CountryMatched.objects.all()
        self.assertEqual(country_matched.count(), 1)
        self.assertEqual(country_matched.first().matched.all()[0].status, "MATCHED")
        self.assertEqual(country_matched.first().matched.all()[1].status, "MATCHED")
        self.assertEqual(country_matched.first().matched.all()[2].status, "MATCHED")
        self.assertEqual(country_matched.first().official, models.Country.objects.get(name="Brazil", acronym="BR", status="OFFICIAL"))
        self.assertEqual(country_matched.first().matched.count(), 3)
        self.assertEqual(set(country_matched.first().matched.values_list("name", flat=True)), set(['Brasile', 'Brasil', 'Brasill']))

    def test_apply_fuzzy_matched_countries(self):
        matches = normalize_countries.Command().auto_create_fuzzy_matches(threshold=70)
        official = models.Country.objects.get(name="Brazil", status="OFFICIAL")
        normalize_countries.Command().apply_fuzzy_matched_countries(name="Brazil")
        self.location1.refresh_from_db()
        self.location2.refresh_from_db()
        self.location3.refresh_from_db()
        self.assertEqual(self.location1.country, official)
        self.assertEqual(self.location2.country, official)
        self.assertEqual(self.location3.country, official)

    def test_unset_matched_countries(self):
        self.country_status_matched = models.Country.objects.create(
            creator=self.user,
            name="Pais teste",
            status="MATCHED"
        )
        matches = normalize_countries.Command().auto_create_fuzzy_matches(threshold=70)
        official = models.Country.objects.get(name="Brazil", status="OFFICIAL")
        normalize_countries.Command().apply_fuzzy_matched_countries(name="Brazil")
        normalize_countries.Command().unset_matched_countries(name="Brazil")
        self.assertEqual(models.CountryMatched.objects.first().matched.count(), 0)