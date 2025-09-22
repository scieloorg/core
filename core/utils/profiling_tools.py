# profiling_tools.py - Versão expandida com suporte a métodos e properties

import functools
import logging
import time

import psutil
from django.conf import settings
from django.db import connection

# Ativa/desativa profiling via settings
PROFILING_ENABLED = getattr(settings, "PROFILING_ENABLED", False)
PROFILING_LOG_ALL = getattr(settings, "PROFILING_LOG_ALL", False)
PROFILING_LOG_SLOW_REQUESTS = getattr(
    settings, "PROFILING_LOG_SLOW_REQUESTS", 0.4
)  # segundos
PROFILING_LOG_HIGH_MEMORY = getattr(settings, "PROFILING_LOG_HIGH_MEMORY", 40)  # MB

profiling_logger = logging.getLogger("profiling")
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
            if (duration > PROFILING_LOG_SLOW_REQUESTS) or (
                memory_used > PROFILING_LOG_HIGH_MEMORY
            ):
                profiling_logger.warning(f"Slow {msg}")
                # Se muito lento, log das queries mais demoradas
                if duration > PROFILING_LOG_SLOW_REQUESTS * 2:
                    slow_queries = sorted(
                        connection.queries[start_queries:end_queries],
                        key=lambda x: float(x.get("time", 0)),
                        reverse=True,
                    )[:3]

                    for i, query in enumerate(slow_queries, 1):
                        profiling_logger.warning(
                            f"  Slow query #{i}: {query['time']}s - {query['sql'][:100]}..."
                        )
            elif PROFILING_LOG_ALL:
                profiling_logger.warning(msg)

            # Adiciona headers opcionais
            if hasattr(response, "headers"):
                response["X-Response-Time"] = f"{duration:.3f}"
                if settings.DEBUG:
                    response["X-DB-Queries"] = str(queries_count)
                    response["X-Memory-Used"] = f"{memory_used:.1f}"

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
            "class": cls.__name__,
            "method": func.__name__,
            "user": "unknown",
            "filename": "unknown",
        }

        # Tenta extrair user e filename dos argumentos conhecidos
        # Para register(cls, xml_with_pre, filename, user, ...)
        if len(args) >= 3:
            if hasattr(args[2], "username"):  # user
                method_info["user"] = args[2].username
            if len(args) >= 2 and isinstance(args[1], str):  # filename
                method_info["filename"] = args[1]

        # Verifica kwargs também
        method_info["user"] = getattr(
            kwargs.get("user"), "username", method_info["user"]
        )
        method_info["filename"] = kwargs.get("filename", method_info["filename"])

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
            if (duration > PROFILING_LOG_SLOW_REQUESTS) or (
                memory_used > PROFILING_LOG_HIGH_MEMORY
            ):
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


def profile_method(func):
    """
    Decorador para métodos padrão de instância
    Uso: @profile_method em qualquer método de classe
    """
    if not PROFILING_ENABLED:
        return func

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Informações do método
        method_info = {
            "class": self.__class__.__name__,
            "method": func.__name__,
            "instance_id": getattr(self, "id", getattr(self, "pk", "no_id")),
        }

        # Profiling
        process = psutil.Process()
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024
        start_queries = len(connection.queries)

        try:
            result = func(self, *args, **kwargs)

            # Métricas
            duration = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory
            queries_count = len(connection.queries) - start_queries

            # Log
            msg = (
                f"method | "
                f"{method_info['class']}.{method_info['method']} | "
                f"instance: {method_info['instance_id']} | "
                f"duration: {duration:.2f}s | "
                f"memory: +{memory_used:.1f}MB | "
                f"queries: {queries_count}"
            )

            if (duration > PROFILING_LOG_SLOW_REQUESTS) or (
                memory_used > PROFILING_LOG_HIGH_MEMORY
            ):
                profiling_logger.warning(f"Slow {msg}")

                # Log queries lentas se muito devagar
                if duration > PROFILING_LOG_SLOW_REQUESTS * 2 and queries_count > 0:
                    slow_queries = sorted(
                        connection.queries[
                            start_queries : start_queries + queries_count
                        ],
                        key=lambda x: float(x.get("time", 0)),
                        reverse=True,
                    )[:3]

                    for i, query in enumerate(slow_queries, 1):
                        profiling_logger.warning(
                            f"  Query #{i}: {query['time']}s - {query['sql'][:100]}..."
                        )
            elif PROFILING_LOG_ALL:
                profiling_logger.info(msg)

            return result

        except Exception as e:
            duration = time.time() - start_time
            profiling_logger.error(
                f"Method failed | "
                f"{method_info['class']}.{method_info['method']} | "
                f"duration: {duration:.2f}s | "
                f"error: {str(e)}"
            )
            raise

    return wrapper


def profile_property(func):
    """
    Decorador para @property
    Uso:
        @property
        @profile_property
        def my_property(self):
            return self.calculate_something()
    """
    if not PROFILING_ENABLED:
        return func

    @functools.wraps(func)
    def wrapper(self):
        # Informações da property
        prop_info = {
            "class": self.__class__.__name__,
            "property": func.__name__,
            "instance_id": getattr(self, "id", getattr(self, "pk", "no_id")),
        }

        # Profiling leve para properties (sem psutil a cada chamada)
        start_time = time.time()
        start_queries = len(connection.queries)

        try:
            result = func(self)

            # Métricas
            duration = time.time() - start_time
            queries_count = len(connection.queries) - start_queries

            # Log apenas se lento (properties devem ser rápidas)
            if (
                duration > PROFILING_LOG_SLOW_REQUESTS / 2
            ):  # Threshold menor para properties
                msg = (
                    f"property | "
                    f"{prop_info['class']}.{prop_info['property']} | "
                    f"instance: {prop_info['instance_id']} | "
                    f"duration: {duration:.3f}s | "
                    f"queries: {queries_count}"
                )
                profiling_logger.warning(f"Slow {msg}")
            elif PROFILING_LOG_ALL and duration > 0.01:  # Log apenas se > 10ms
                profiling_logger.info(
                    f"property | {prop_info['class']}.{prop_info['property']} | "
                    f"duration: {duration:.3f}s"
                )

            return result

        except Exception as e:
            duration = time.time() - start_time
            profiling_logger.error(
                f"Property failed | "
                f"{prop_info['class']}.{prop_info['property']} | "
                f"duration: {duration:.3f}s | "
                f"error: {str(e)}"
            )
            raise

    return wrapper


def profile_cached_property(func):
    """
    Decorador para @cached_property do Django
    Uso:
        from django.utils.functional import cached_property

        @cached_property
        @profile_cached_property
        def expensive_calculation(self):
            return self.do_heavy_work()
    """
    if not PROFILING_ENABLED:
        return func

    @functools.wraps(func)
    def wrapper(self):
        # Verifica se já está em cache
        cache_attr = f"_{func.__name__}"
        is_cached = hasattr(self, cache_attr)

        prop_info = {
            "class": self.__class__.__name__,
            "property": func.__name__,
            "instance_id": getattr(self, "id", getattr(self, "pk", "no_id")),
            "cached": is_cached,
        }

        if is_cached and not PROFILING_LOG_ALL:
            # Se já está em cache e não estamos logando tudo, retorna direto
            return func(self)

        start_time = time.time()
        start_queries = len(connection.queries) if not is_cached else 0

        try:
            result = func(self)

            if not is_cached:  # Log apenas no primeiro cálculo
                duration = time.time() - start_time
                queries_count = len(connection.queries) - start_queries

                msg = (
                    f"cached_property (first call) | "
                    f"{prop_info['class']}.{prop_info['property']} | "
                    f"instance: {prop_info['instance_id']} | "
                    f"duration: {duration:.3f}s | "
                    f"queries: {queries_count}"
                )

                if duration > PROFILING_LOG_SLOW_REQUESTS:
                    profiling_logger.warning(f"Slow {msg}")
                elif PROFILING_LOG_ALL:
                    profiling_logger.info(msg)

            return result

        except Exception as e:
            duration = time.time() - start_time
            profiling_logger.error(
                f"Cached property failed | "
                f"{prop_info['class']}.{prop_info['property']} | "
                f"duration: {duration:.3f}s | "
                f"error: {str(e)}"
            )
            raise

    return wrapper


def profile_function(func):
    """
    Decorador para funções standalone (não métodos)
    Uso:
        @profile_function
        def process_data(data):
            return data.upper()
    """
    if not PROFILING_ENABLED:
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Informações da função
        func_info = {
            "function": func.__name__,
            "module": func.__module__,
            "args_count": len(args),
            "kwargs_count": len(kwargs),
        }

        # Tenta extrair informações úteis dos argumentos
        # Por exemplo, se o primeiro arg for um Model Django
        if args and hasattr(args[0], "__class__"):
            arg_class = args[0].__class__.__name__
            if hasattr(args[0], "pk") or hasattr(args[0], "id"):
                func_info["first_arg"] = (
                    f"{arg_class}(id={getattr(args[0], 'pk', getattr(args[0], 'id', 'unknown'))})"
                )
            else:
                func_info["first_arg"] = arg_class

        process = psutil.Process()
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024
        start_queries = len(connection.queries)

        try:
            result = func(*args, **kwargs)

            # Métricas
            duration = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory
            queries_count = len(connection.queries) - start_queries

            # Informações adicionais sobre o resultado
            result_info = ""
            if result is not None:
                if hasattr(result, "__len__"):
                    result_info = f" | result_len: {len(result)}"
                elif hasattr(result, "count"):
                    try:
                        result_info = f" | result_count: {result.count()}"
                    except:
                        pass

            msg = (
                f"function | "
                f"{func_info['module']}.{func_info['function']} | "
                f"args: {func_info['args_count']}, kwargs: {func_info['kwargs_count']} | "
                f"duration: {duration:.2f}s | "
                f"memory: +{memory_used:.1f}MB | "
                f"queries: {queries_count}"
                f"{result_info}"
            )

            # Adiciona info do primeiro argumento se disponível
            if "first_arg" in func_info:
                msg = msg.replace(
                    " | args:", f" | first_arg: {func_info['first_arg']} | args:"
                )

            if (duration > PROFILING_LOG_SLOW_REQUESTS) or (
                memory_used > PROFILING_LOG_HIGH_MEMORY
            ):
                profiling_logger.warning(f"Slow {msg}")

                # Log queries lentas
                if duration > PROFILING_LOG_SLOW_REQUESTS * 2 and queries_count > 0:
                    slow_queries = sorted(
                        connection.queries[
                            start_queries : start_queries + queries_count
                        ],
                        key=lambda x: float(x.get("time", 0)),
                        reverse=True,
                    )[:3]

                    for i, query in enumerate(slow_queries, 1):
                        profiling_logger.warning(
                            f"  Query #{i}: {query['time']}s - {query['sql'][:100]}..."
                        )
            elif PROFILING_LOG_ALL:
                profiling_logger.info(msg)

            return result

        except Exception as e:
            duration = time.time() - start_time
            profiling_logger.error(
                f"Function failed | "
                f"{func_info['module']}.{func_info['function']} | "
                f"duration: {duration:.2f}s | "
                f"error: {str(e)}"
            )
            raise

    return wrapper


# Decorator para staticmethod
def profile_staticmethod(func):
    """
    Decorador para @staticmethod
    Uso:
        @staticmethod
        @profile_staticmethod
        def utility_function(param1, param2):
            return param1 + param2
    """
    if not PROFILING_ENABLED:
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Para staticmethod, não temos self/cls
        method_info = {"function": func.__name__, "module": func.__module__}

        process = psutil.Process()
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024
        start_queries = len(connection.queries)

        try:
            result = func(*args, **kwargs)

            duration = time.time() - start_time
            memory_used = process.memory_info().rss / 1024 / 1024 - start_memory
            queries_count = len(connection.queries) - start_queries

            msg = (
                f"staticmethod | "
                f"{method_info['module']}.{method_info['function']} | "
                f"duration: {duration:.2f}s | "
                f"memory: +{memory_used:.1f}MB | "
                f"queries: {queries_count}"
            )

            if (duration > PROFILING_LOG_SLOW_REQUESTS) or (
                memory_used > PROFILING_LOG_HIGH_MEMORY
            ):
                profiling_logger.warning(f"Slow {msg}")
            elif PROFILING_LOG_ALL:
                profiling_logger.info(msg)

            return result

        except Exception as e:
            duration = time.time() - start_time
            profiling_logger.error(
                f"Staticmethod failed | "
                f"{method_info['module']}.{method_info['function']} | "
                f"duration: {duration:.2f}s | "
                f"error: {str(e)}"
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
        if request.path.startswith("/static/") or request.path.startswith("/media/"):
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


# ===== EXEMPLOS DE USO =====

"""
# 1. Função standalone
@profile_function
def process_csv_file(filepath, delimiter=','):
    # Processa arquivo CSV
    with open(filepath, 'r') as f:
        data = f.read()
    return data.split(delimiter)


# 2. Função com Model Django como argumento
@profile_function
def send_notification(user, message):
    # user será identificado no log como User(id=123)
    notification.send(user, message)
    return True


# 3. Função que retorna QuerySet
@profile_function
def get_active_articles(category=None):
    qs = Article.objects.filter(active=True)
    if category:
        qs = qs.filter(category=category)
    return qs  # Log mostrará result_count


# 4. Método de instância padrão
class MyModel(models.Model):
    @profile_method
    def calculate_statistics(self):
        # Seu código aqui
        return stats


# 5. Property simples
class Article(models.Model):
    @property
    @profile_property
    def word_count(self):
        return len(self.content.split())


# 6. Cached property do Django
from django.utils.functional import cached_property

class Document(models.Model):
    @cached_property
    @profile_cached_property
    def processed_content(self):
        # Processamento pesado que será cacheado
        return self.heavy_processing()


# 7. Static method
class DataProcessor:
    @staticmethod
    @profile_staticmethod
    def process_batch(data_list):
        # Processamento em lote
        return processed_data


# 8. Class method (já existente no seu código)
class XMLHandler:
    @classmethod
    @profile_classmethod
    def parse_xml(cls, xml_content):
        # Parse XML
        return parsed_data


# 9. Property com parâmetros customizados
class ComplexModel(models.Model):
    @property
    @profile_property
    def complex_calculation(self):
        # Se quiser um threshold diferente para esta property específica
        # pode criar um decorador customizado:
        # @profile_property_custom(threshold=0.1)
        return self.do_complex_math()


# 10. Em Views/ViewSets (já existente)
class MyViewSet(viewsets.ModelViewSet):
    @profile_endpoint
    def create(self, request):
        # Sua lógica aqui
        return Response(data)


# 11. Funções utilitárias
@profile_function
def calculate_hash(data):
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()


# 12. Funções com decoradores múltiplos
from django.core.cache import cache

@profile_function
@cache.cache_page(60 * 15)
def expensive_calculation(param1, param2):
    # Cálculo pesado
    return result
"""
