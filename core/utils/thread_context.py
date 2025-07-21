import threading

_thread_locals = threading.local()

def set_current_collections(collection):
    """Define a coleção atual no contexto da thread"""
    _thread_locals.collection = collection

def get_current_collections():
    """Retorna a coleção atual da thread"""
    return getattr(_thread_locals, 'collection', None)

def clear_current_collections():
    """Limpa a coleção atual da thread"""
    if hasattr(_thread_locals, 'collection'):
        delattr(_thread_locals, 'collection')

def set_current_user(user):
    """Define o usuário atual no contexto da thread"""
    _thread_locals.user = user

def get_current_user():
    """Retorna o usuário atual da thread"""
    return getattr(_thread_locals, 'user', None)