# profiling_tools.py - Coloque em algum lugar do seu projeto (ex: utils/profiling_tools.py)

import time
import functools
import psutil
import logging
from django.db import connection
from django.conf import settings

# Ativa/desativa profiling via settings
PROFILING_ENABLED = getattr(settings, 'PROFILING_ENABLED', False)
PROFILING_LOG_ALL = getattr(settings, 'PROFILING_LOG_ALL', False)
PROFILING_LOG_SLOW_REQUESTS = getattr(settings, 'PROFILING_LOG_SLOW_REQUESTS', 0.4)  # segundos
PROFILING_LOG_HIGH_MEMORY = getattr(settings, 'PROFILING_LOG_HIGH_MEMORY', 40)  # MB

profiling_logger = logging.getLogger('profiling')
profiling_logger.warning(f"PROFILING_ENABLED={PROFILING_ENABLED}")
profiling_logger.warning(f"PROFILING_LOG_ALL={PROFILING_LOG_ALL}")
profiling_logger.warning(f"PROFILING_LOG_SLOW_REQUESTS={PROFILING_LOG_SLOW_REQUESTS}")
profiling_logger.warning(f"PROFILING_LOG_HIGH_MEMORY={PROFILING_LOG_HIGH_MEMORY}")


def profile_endpoint(func):
    """
    Decorador minimalista para profiling
    Uso: @profile_endpoint no método create()
    """
    if not PROFILING_ENABLED:
        return func
    
    @functools.wraps(func)
    def wrapper(self, request, *args, **kwargs):
        # Dados iniciais

        process = psutil.Process()
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_queries = len(connection.queries)
        
        try:
            # Executa função original
            response = func(self, request, *args, **kwargs)
            
            # Coleta métricas finais
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024
            end_queries = len(connection.queries)
            
            # Calcula diferenças
            duration = end_time - start_time
            memory_used = end_memory - start_memory
            queries_count = end_queries - start_queries

            msg = (
                f"request detected | "
                f"endpoint: {request.path} | "
                f"duration: {duration:.2f}s | "
                f"memory: +{memory_used:.1f}MB | "
                f"queries: {queries_count} | "
                f"user: {getattr(request.user, 'username', 'anonymous')}"
            )
            
            #  Log apenas se for relevante
            if (duration > PROFILING_LOG_SLOW_REQUESTS) or (memory_used > PROFILING_LOG_HIGH_MEMORY):
                profiling_logger.warning(f"Slow {msg}")
                # Se muito lento, log das queries mais demoradas
                if duration > PROFILING_LOG_SLOW_REQUESTS * 2:
                    slow_queries = sorted(
                        connection.queries[start_queries:end_queries],
                        key=lambda x: float(x.get('time', 0)),
                        reverse=True
                    )[:3]
                    
                    for i, query in enumerate(slow_queries, 1):
                        profiling_logger.warning(
                            f"  Slow query #{i}: {query['time']}s - {query['sql'][:100]}..."
                        )
            elif PROFILING_LOG_ALL:
                profiling_logger.warning(msg)

            # Adiciona headers opcionais
            if hasattr(response, 'headers'):
                response['X-Response-Time'] = f"{duration:.3f}"
                if settings.DEBUG:
                    response['X-DB-Queries'] = str(queries_count)
                    response['X-Memory-Used'] = f"{memory_used:.1f}"
            
            return response
            
        except Exception as e:
            # Log erro mas não interfere
            duration = time.time() - start_time
            profiling_logger.error(
                f"Request failed | endpoint: {request.path} | "
                f"duration: {duration:.2f}s | error: {str(e)}"
            )
            raise
    
    return wrapper


def profile_classmethod(func):
    """
    Versão específica para @classmethod
    """
    if not PROFILING_ENABLED:
        return func
    
    @functools.wraps(func)
    def wrapper(cls, *args, **kwargs):
        # Extrai informações específicas para PidProviderXML.register
        method_info = {
            'class': cls.__name__,
            'method': func.__name__,
            'user': 'unknown',
            'filename': 'unknown'
        }
        
        # Tenta extrair user e filename dos argumentos conhecidos
        # Para register(cls, xml_with_pre, filename, user, ...)
        if len(args) >= 3:
            if hasattr(args[2], 'username'):  # user
                method_info['user'] = args[2].username
            if len(args) >= 2 and isinstance(args[1], str):  # filename
                method_info['filename'] = args[1]
        
        # Verifica kwargs também
        method_info['user'] = getattr(kwargs.get('user'), 'username', method_info['user'])
        method_info['filename'] = kwargs.get('filename', method_info['filename'])
        
        # Profiling
        process = psutil.Process()
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024
        start_queries = len(connection.queries)
        
        try:
            result = func(cls, *args, **kwargs)
            
            # Métricas
            duration = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory
            queries_count = len(connection.queries) - start_queries
            
            # Log
            msg = (
                f"classmethod | "
                f"{method_info['class']}.{method_info['method']} | "
                f"duration: {duration:.2f}s | "
                f"memory: +{memory_used:.1f}MB | "
                f"queries: {queries_count} | "
                f"user: {method_info['user']} | "
                f"file: {method_info['filename']}"
            )
            if (duration > PROFILING_LOG_SLOW_REQUESTS) or (memory_used > PROFILING_LOG_HIGH_MEMORY):
                profiling_logger.warning(f"Slow {msg}")
            elif PROFILING_LOG_ALL:
                profiling_logger.warning(msg)            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            profiling_logger.error(
                f"Classmethod failed | "
                f"{method_info['class']}.{method_info['method']} | "
                f"duration: {duration:.2f}s | "
                f"error: {str(e)} | "
                f"user: {method_info['user']}"
            )
            raise
    
    return wrapper


# middleware.py - Alternativa ao decorador
class LightweightProfilingMiddleware:
    """
    Middleware minimalista de profiling
    Monitora TODAS as requisições automaticamente
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.process = psutil.Process()
        
    def __call__(self, request):
        if not PROFILING_ENABLED:
            return self.get_response(request)
        
        # Pula arquivos estáticos
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        memory_delta = self.process.memory_info().rss / 1024 / 1024 - start_memory
        
        # Log apenas requisições problemáticas
        if duration > PROFILING_LOG_SLOW_REQUESTS:
            profiling_logger.warning(
                f"Slow: {request.method} {request.path} - "
                f"{duration:.2f}s - {memory_delta:+.1f}MB"
            )
        
        return response
