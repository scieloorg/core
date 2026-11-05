from django.middleware.locale import LocaleMiddleware as DjangoLocaleMiddleware

from core.utils.thread_context import (
    clear_current_collections,
    set_current_collections,
    set_current_user,
)


class LocaleMiddleware(DjangoLocaleMiddleware):
    def process_response(self, request, response):
        # O LocaleMiddleware do Django redireciona qualquer 404 sem prefixo de
        # idioma para /<lang>/<path>, e o catch-all do Wagtail em i18n_patterns
        # torna esse destino sempre válido. Um 404 vindo de uma view resolvida
        # (ex.: API) é a resposta final e não deve virar redirect.
        if response.status_code == 404 and request.resolver_match is not None:
            return response
        return super().process_response(request, response)


class UserCollectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Limpa dados da thread anterior (por segurança)
        clear_current_collections()

        if request.user.is_authenticated:
            set_current_user(request.user)
            collections = request.user.collection.all()
            set_current_collections(collections)

            request.user_collection = collections
        else:
            set_current_user(None)
            set_current_collections(None)
            request.user_collection = None

        response = self.get_response(request)

        # Limpa após o processamento
        clear_current_collections()

        return response
