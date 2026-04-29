from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="FMiraeekXCSl3zHfg7D4oHx7ufT46HRnwnsawKgTCC53BYajVkVzb8HhOvBOHakR",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "192.168.1.98"]

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
        "LOCATION": "redis://redis:6379",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = env("EMAIL_HOST", default="mailhog")
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa F405

MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]
# # django-debug-toolbar
# # ------------------------------------------------------------------------------
# # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
# INSTALLED_APPS += ["debug_toolbar"]  # noqa F405
# # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
# MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa F405
# # https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
# DEBUG_TOOLBAR_CONFIG = {
#     "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
#     "SHOW_TEMPLATE_CONTEXT": True,
# }
# # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
if env("USE_DOCKER") == "yes":
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions", "silk"]  # noqa F405
# Celery
# ------------------------------------------------------------------------------

# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True

# OpenSearch logging (development)
# ------------------------------------------------------------------------------
# Re-evaluate OpenSearch environment / index defaults for the development
# environment. ``OPENSEARCH_LOGGING_ENVIRONMENT`` defaults to ``"dev"`` here
# (overridable via env var), and the index name is recomposed so dev logs
# land in a clearly-separated index such as ``core-logs-dev-2026.04.28``.
#
# To exercise the OpenSearch sink locally, set ``USE_OPENSEARCH_LOGGING=yes``
# in ``.envs/.local/.django`` — the ``opensearch`` service in ``local.yml``
# will be used as the default host (http://opensearch:9200, no SSL). Leaving
# the flag unset keeps the existing behavior (console-only logging).
OPENSEARCH_LOGGING_ENVIRONMENT = env.str(
    "OPENSEARCH_LOGGING_ENVIRONMENT", default="dev"
)
OPENSEARCH_LOGGING_INDEX = env.str(  # noqa: F405
    "OPENSEARCH_LOGGING_INDEX",
    default=f"{OPENSEARCH_LOGGING_INDEX_BASE}-{OPENSEARCH_LOGGING_ENVIRONMENT}",  # noqa: F405
)
# Reasonable defaults for the local docker-compose ``opensearch`` service:
# unauthenticated, plain HTTP, single node.
if not OPENSEARCH_LOGGING_HOSTS:  # noqa: F405
    OPENSEARCH_LOGGING_HOSTS = env.list(
        "OPENSEARCH_LOGGING_HOSTS", default=["http://opensearch:9200"]
    )
OPENSEARCH_LOGGING_USE_SSL = env.bool("OPENSEARCH_LOGGING_USE_SSL", default=False)
OPENSEARCH_LOGGING_VERIFY_CERTS = env.bool(
    "OPENSEARCH_LOGGING_VERIFY_CERTS", default=False
)

# Patch the LOGGING dict inherited from base.py so it picks up the
# development-specific OpenSearch settings without rebuilding the whole
# dict. Whether the ``opensearch`` handler is actually attached to the
# loggers is still controlled by ``USE_OPENSEARCH_LOGGING`` (computed in
# base.py): unset/false ⇒ console only; true + a host ⇒ console + opensearch.
_opensearch_handler_enabled = bool(USE_OPENSEARCH_LOGGING and OPENSEARCH_LOGGING_HOSTS)  # noqa: F405
LOGGING["handlers"]["opensearch"].update(  # noqa: F405
    {
        "hosts": OPENSEARCH_LOGGING_HOSTS if _opensearch_handler_enabled else [],
        "index": OPENSEARCH_LOGGING_INDEX,
        "use_ssl": OPENSEARCH_LOGGING_USE_SSL,
        "verify_certs": OPENSEARCH_LOGGING_VERIFY_CERTS,
    }
)
LOGGING["handlers"]["opensearch"]["extra_fields"]["environment"] = (  # noqa: F405
    OPENSEARCH_LOGGING_ENVIRONMENT
)
_default_log_handlers = ["console"] + (
    ["opensearch"] if _opensearch_handler_enabled else []
)
LOGGING["root"]["handlers"] = _default_log_handlers  # noqa: F405
LOGGING["loggers"]["django"]["handlers"] = _default_log_handlers  # noqa: F405

# Your stuff...
# ------------------------------------------------------------------------------
