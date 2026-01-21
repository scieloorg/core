
import logging
import re

from django.contrib.auth import get_user_model
from django.db import IntegrityError

from location.models import Location

User = get_user_model()
logger = logging.getLogger(__name__)

def remove_html_tags(text):
    """Remove tags HTML completas e resíduos de tags"""
    # Remove tags HTML completas: <tag>...</tag> ou <tag />
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove resíduos de abertura de tags: <letra
    # Exemplo: "<iSão Paulo" → "São Paulo"
    text = re.sub(r'<[a-zA-Z]+', '', text)
    
    # Remove resíduos de fechamento de tags: letra>
    # Exemplo: "São Pauloi>" → "São Paulo"
    text = re.sub(r'[a-zA-Z]>', '', text)
    
    return text

def remove_unaccent(name):
    if not name:
        return name

    name = remove_html_tags(str(name))

    # Se o nome for apenas números
    if re.fullmatch(r'\s*\d+\s*', name):
        return name

    # Remove caracteres especiais, mantendo acentos
    name = re.sub(r'[^a-zA-ZÀ-ÿ\s]', '', name)

    name = ' '.join(name.split())

    return name

def capitalize(name):
    return name.title() if name else name

def clean_name(name):
    name_clean = remove_unaccent(name)
    return capitalize(name_clean)

def clean_acronym(acronym):
    """Limpa acronym preservando maiúsculas"""
    if not acronym:
        return acronym
    # Remove apenas espaços e caracteres especiais, mantém maiúsculas
    acronym = remove_html_tags(str(acronym))
    acronym = re.sub(r'[^A-Z0-9]', '', acronym.upper())
    return acronym if acronym else None

def choose_canonical_country(countries):
    canonical_country = (
        countries.filter(
        acronym__isnull=False,
        acron3__isnull=False
    ).first() or 
    countries.filter(
        acronym__isnull=False,
    ).first() or
    countries.first()
    )
    logging.info(f"Canonicial chosen: {canonical_country.name} (ID: {canonical_country.id})")
    return canonical_country

def process_duplicates_countries(duplicates, canonical_country, total_deleted):
    """Processa países duplicados, movendo locations e deletando"""

    locations_moved = 0

    for duplicate in duplicates:
        duplicate_locations = duplicate.location_set.all()
        
        for location in duplicate_locations:
            try:
                existing = Location.objects.filter(
                    country=canonical_country,
                    state=location.state,
                    city=location.city
                ).first()
                
                if existing:
                    logging.info(f"Location já existe com país canônico: {location.id} -> {existing.id}")
                    location.delete()
                else:
                    location.country = canonical_country
                    location.save()
                    locations_moved += 1
            except IntegrityError as e:
                logging.error(f"Erro ao atualizar location {location.id}: {e}")
                continue
        
        duplicate.delete()
        total_deleted += 1
    
    return locations_moved


def choose_canonical_state(states):
    """Escolhe o estado canônico entre duplicatas
    Prioridade: 1) com acronym preenchido, 2) mais antigo
    """
    canonical_state = (
        states.filter(acronym__isnull=False).first() or
        states.first()
    )
    logging.info(f"Canonical state chosen: {canonical_state.name} (ID: {canonical_state.id})")
    return canonical_state


def process_duplicates_states(duplicates, canonical_state, total_deleted):
    """Processa estados duplicados, movendo locations e deletando"""    
    locations_moved = 0
    
    for duplicate in duplicates:
        duplicate_locations = duplicate.location_set.all()
        
        for location in duplicate_locations:
            try:
                existing = Location.objects.filter(
                    country=location.country,
                    state=canonical_state,
                    city=location.city
                ).first()
                
                if existing:
                    logging.info(f"Location já existe com estado canônico: {location.id} -> {existing.id}")
                    location.delete()
                else:
                    location.state = canonical_state
                    location.save()
                    locations_moved += 1
            except IntegrityError as e:
                logging.error(f"Erro ao atualizar location {location.id}: {e}")
                continue
        
        duplicate.delete()
        total_deleted += 1
    
    return locations_moved
