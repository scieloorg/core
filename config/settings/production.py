import logging

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["example.com"])

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"] = env.db("DATABASE_URL")  # noqa F405
DATABASES["default"]["ATOMIC_REQUESTS"] = True  # noqa F405
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa F405
DATABASES["default"]["ENGINE"] = 'django_prometheus.db.backends.postgresql'
# Melhoria: Usando variáveis de ambiente para OPTIONS e POOL_OPTIONS com defaults
DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": env.int("DB_CONNECT_TIMEOUT", default=10),
    # Adicione outras opções de conexão aqui se necessário
}
DATABASES["default"]["POOL_OPTIONS"] = {
    'POOL_SIZE': env.int("DB_POOL_SIZE", default=10),
    'MAX_OVERFLOW': env.int("DB_MAX_OVERFLOW", default=20),
    'RECYCLE': env.int("DB_RECYCLE", default=300),
    # Adicione outras opções do pool aqui se necessário
}

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF", default=True
)

# Duração máxima da sessão em segundos. Padrão: 30 minutos (1800s).
# Sobrescreva com a variável de ambiente DJANGO_SESSION_COOKIE_AGE. Ex: export DJANGO_SESSION_COOKIE_AGE=3600
SESSION_COOKIE_AGE = env.int('DJANGO_SESSION_COOKIE_AGE', 30 * 60)

# Se o cookie da sessão expira ao fechar o navegador. Padrão: True (conforme 'true' no getenv).
# Sobrescreva com DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE=False para persistir.
# Ex: export DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE=False
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool('DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE', True)

# Salva a sessão a cada requisição. Essencial para timeout por inatividade. Padrão: True.
# Sobrescreva com DJANGO_SESSION_SAVE_EVERY_REQUEST=False para desativar.
# Ex: export DJANGO_SESSION_SAVE_EVERY_REQUEST=False
SESSION_SAVE_EVERY_REQUEST = env.bool('DJANGO_SESSION_SAVE_EVERY_REQUEST', True)

# STATIC
# ------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
# MEDIA
# ------------------------------------------------------------------------------

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="SciELO Content Manager  <suporte.aplicacao@scielo.org>",
)

# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-EMAIL_HOST
EMAIL_HOST = env.str("DJANGO_EMAIL_HOST", default="mailrelay.scielo.org")

# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = env.int("DJANGO_EMAIL_PORT", default=25)

# https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
EMAIL_HOST_USER = env.str("DJANGO_EMAIL_HOST_USER", default="suporte.aplicacao@scielo.org")

# https://docs.djangoproject.com/en/dev/ref/settings/#std-setting-EMAIL_HOST_PASSWORD
EMAIL_HOST_PASSWORD = env.str("DJANGO_EMAIL_HOST_PASSWORD", default="")

# https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
EMAIL_USE_TLS = env.bool("DJANGO_EMAIL_USE_TLS", default=False)

# https://docs.djangoproject.com/en/dev/ref/settings/#email-use-ssl
EMAIL_USE_SSL = env.bool("DJANGO_EMAIL_USE_SSL", default=False)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[SciELO Content Manager ]",
)

# ADMIN
# ------------------------------------------------------------------------------
# Admin URL regex.
DJANGO_ADMIN_URL = env("DJANGO_ADMIN_URL")
WAGTAIL_ADMIN_URL = env("WAGTAIL_ADMIN_URL")

# Anymail
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ["anymail"]  # noqa F405
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# https://anymail.readthedocs.io/en/stable/esps
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
ANYMAIL = {}

# django-compressor
# ------------------------------------------------------------------------------
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_ENABLED
COMPRESS_ENABLED = env.bool("COMPRESS_ENABLED", default=True)
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_STORAGE
COMPRESS_STORAGE = "compressor.storage.GzipCompressorFileStorage"
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_URL
COMPRESS_URL = STATIC_URL  # noqa F405
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_OFFLINE
COMPRESS_OFFLINE = True  # Offline compression is required when using Whitenoise
# https://django-compressor.readthedocs.io/en/latest/settings/#django.conf.settings.COMPRESS_FILTERS
COMPRESS_FILTERS = {
    "css": [
        "compressor.filters.css_default.CssAbsoluteFilter",
        "compressor.filters.cssmin.rCSSMinFilter",
    ],
    "js": ["compressor.filters.jsmin.JSMinFilter"],
}

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

if env.bool("USE_SENTRY", default=False):
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "verbose": {
                "format": "%(levelname)s %(asctime)s %(module)s "
                "%(process)d %(thread)d %(message)s"
            }
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "profiling_file": {
                "level": "DEBUG",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": APPS_DIR / "media" / "profiling-prod.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 30,  # Mantém 30 dias
                "formatter": "simple",
                "encoding": "utf-8",
            },
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        "loggers": {
            "django.db.backends": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
            # Errors logged by the SDK itself
            "sentry_sdk": {"level": "ERROR", "handlers": ["console"], "propagate": False},
            "django.security.DisallowedHost": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
            # Celery Signals
            "config.celery_signals": {
                "handlers": ["console"],
                "level": "DEBUG", # ESSENCIAL: para ver a mensagem de depuração
                "propagate": False, # Não envie para o logger pai (root), para ter controle total
            },
            "profiling": {  # <-- Logger usado pelo decorador
                "handlers": ["profiling_file"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }

    # Sentry
    # ------------------------------------------------------------------------------
    SENTRY_DSN = env("SENTRY_DSN")
    SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)

    sentry_logging = LoggingIntegration(
        level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )
    integrations = [
        sentry_logging,
        DjangoIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
    ]
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=integrations,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=1.0),
        enable_tracing=True,
    )

# Your stuff...
# ------------------------------------------------------------------------------
