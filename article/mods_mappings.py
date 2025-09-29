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

STRUCTURAL_SECTIONS = {
    'editorial', 'erratum', 'errata', 'correction', 'retraction',
    'nominata', 'instructions', 'guidelines', 'normas',
    'instruções', 'diretrizes', 'acknowledgments', 'agradecimentos',
    'index', 'índice', 'sumário', 'contents'
}

POLICIES = {
            'scl': 'Open access following SciELO Brazil editorial criteria',
            'arg': 'Open access following SciELO Argentina editorial criteria',
            'chl': 'Open access following SciELO Chile editorial criteria',
            'col': 'Open access following SciELO Colombia editorial criteria',
            'cub': 'Open access following SciELO Cuba editorial criteria',
            'esp': 'Open access following SciELO Spain editorial criteria',
            'mex': 'Open access following SciELO Mexico editorial criteria',
            'per': 'Open access following SciELO Peru editorial criteria',
            'prt': 'Open access following SciELO Portugal editorial criteria',
            'psi': 'Open access following SciELO Psychology editorial criteria',
            'sza': 'Open access following SciELO South Africa editorial criteria',
            'ury': 'Open access following SciELO Uruguay editorial criteria',
            'ven': 'Open access following SciELO Venezuela editorial criteria'
        }

MAPPING_OAI_STATUS = {
            "": None,
            "diamond": None,  # Totalmente aberto
            "gold": None,  # Totalmente aberto
            "hybrid": "Hybrid open access model - some content may require subscription",
            "bronze": "Bronze open access - free to read but with copyright restrictions",
            "green": "Green open access - author self-archived version available",
            "closed": "Subscription required for full access"
        }

FORMAT_MEDIA_TYPES = {
                            'crossref': 'application/vnd.crossref.unixsd+xml',
                            'pubmed': 'application/vnd.pubmed+xml',
                            'pmc': 'application/vnd.pmc+xml',
                            'xml': 'text/xml',
                            'html': 'text/html',
                            'pdf': 'application/pdf',
                            'epub': 'application/epub+zip'
                        }
