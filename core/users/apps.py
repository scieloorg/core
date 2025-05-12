from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from wagtail.users.apps import WagtailUsersAppConfig


class CustomUsersAppConfig(WagtailUsersAppConfig):
    user_viewset = "core.users.viewsets.UserViewSet"
    verbose_name = _("Users")

