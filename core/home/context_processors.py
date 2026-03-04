"""
Context processors para a aplicação home.
"""
from core.home.models import HomePage


def sponsors(request):
    """
    Adiciona os sponsors da HomePage ao contexto de todos os templates.
    
    Retorna os sponsors ordenados por sort_order para serem exibidos
    no footer de todas as páginas do site.
    """
    try:
        # Busca a primeira HomePage ativa
        homepage = HomePage.objects.live().first()
        if homepage:
            return {
                'footer_sponsors': homepage.sponsors.select_related('logo').all()
            }
    except Exception:
        pass
    
    return {'footer_sponsors': []}
