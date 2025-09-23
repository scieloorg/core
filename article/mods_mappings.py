"""
Mapeamentos e constantes para metadados OAI-PMH/MODS
"""

MODS_TYPE_OF_RESOURCE_MAPPING = {
    "research-article": "text/digital",
    "review-article": "text/digital",
    "case-report": "text/digital",
    "editorial": "text/digital",
    "letter": "text/digital",
    "brief-report": "text/digital",
    "correction": "text/digital",
    "retraction": "text/digital",
}

DISPLAY_LABEL = {
    'pt': 'Resumo',
    'en': 'Abstract',
    'es': 'Resumen',
}

AUDIENCE_MAPPING = {
    "research-article": "researchers",
    "review-article": "researchers",
    "case-report": "practitioners",
    "editorial": "general",
    "letter": "general",
    "brief-report": "practitioners",
}

ISO_639_1_TO_2B = {
    'pt': 'por', 'en': 'eng', 'es': 'spa', 'fr': 'fre',
    'it': 'ita', 'de': 'ger', 'ru': 'rus', 'zh': 'chi',
    'ja': 'jpn', 'ar': 'ara', 'hi': 'hin'
}

LATIN_SCRIPT_LANGUAGES = {'pt', 'en', 'es', 'fr', 'it', 'de'}
