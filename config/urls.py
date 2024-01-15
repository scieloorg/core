from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtailautocomplete.urls.admin import urlpatterns as autocomplete_admin_urls

from core.api.wagtail.api import api_router

from core.search_site import views as search_views  # noqa isort:skip
from core.users.views import filter_journals

urlpatterns = [
    # path("", TemplateView.as_view(template_name="home/home_page.html"), name="home"),
    # Django Admin, use {% url "admin:index" %}
    # Add Wagtail Autocomplete’s URL patterns to your project’s URL config, usually in urls.py.
    # This should come before your wagtail_urls
    # and if you are using the suggested pattern r'^admin/autocomplete/'
    # it must also come before your admin urls:
    path("admin/autocomplete/", include(autocomplete_admin_urls)),
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    # Wagtail Admin
    path(settings.WAGTAIL_ADMIN_URL, include(wagtailadmin_urls)),
    re_path(r"^documents/", include(wagtaildocs_urls)),
    path("api/v2/pid/", include("config.api_router", namespace="pid_provider")),
    # JWT
    path("api/v2/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(
        "api/v2/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
    # API V1 endpoint to custom models
    path("api/v1/", include("config.api_router")),
    path('filter_journals/', filter_journals, name='filter_journals'),
    # Your stuff: custom urls includes go here
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail’s page serving mechanism. This should be the last pattern in
    # the list:
    # path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    url(r"^pages/", include(wagtail_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Translatable URLs
# These will be available under a language code prefix. For example /en/search/
urlpatterns += i18n_patterns(
    # Site search
    re_path(r"^search_site/$", search_views.search, name="search_site"),
    # Index search
    re_path(r"^search/", include("search.urls")),
    # User management
    path("api/v2/", api_router.urls),
    path("users/", include("core.users.urls", namespace="users")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("allauth.urls")),
    path("", include(wagtail_urls)),
)

if settings.DEBUG:
    # Wagtail settings: Serve static and media files from development server
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
