"""
Context processors para a aplicação home.
"""
from core.home.models import HomePage

from .models import _get_current_locale


def get_homepage_with_language_locale():
    locale = _get_current_locale()
    try:
        return HomePage.objects.get(locale=locale)
    except HomePage.DoesNotExist:
        return HomePage.objects.live().first()


def sponsors(request):
    """
    Adiciona os sponsors da HomePage ao contexto de todos os templates.
    
    Retorna os sponsors ordenados por sort_order para serem exibidos
    no footer de todas as páginas do site.
    """
    try:
        homepage = get_homepage_with_language_locale()
        if homepage:
            return {
                'footer_sponsors': homepage.sponsors.select_related('logo').all()
            }
    except Exception:
        pass
    
    return {'footer_sponsors': []}
