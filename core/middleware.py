from core.utils.thread_context import (
    clear_current_collections,
    set_current_collections,
    set_current_user,
)


class UserCollectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Limpa dados da thread anterior (por segurança)
        clear_current_collections()
        
        if request.user.is_authenticated:
            set_current_user(request.user)
            set_current_collections(request.user.collection.all())

            request.user_collection = request.user.collection.all()
        else:
            set_current_user(None)
            set_current_collections(None)
            request.user_collection = None

        response = self.get_response(request)
        
        # Limpa após o processamento
        clear_current_collections()
        
        return response