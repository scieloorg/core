from django.contrib.auth import get_user_model
from django.db.models import Prefetch

from wagtail.users.views.users import EditView as WagtailUserEditView
from wagtail.users.views.users import UserViewSet as WagtailUserViewSet

from journal.models import Journal

from .forms import CustomUserCreationForm, CustomUserEditForm

User = get_user_model()


class CustomUserEditView(WagtailUserEditView):
    def get_queryset(self):
        return User.objects.prefetch_related(
            Prefetch(
                "journal",
                queryset=Journal.objects.select_related("official"),
            ),
            "collection",
            "groups",
            "user_permissions",
        )


class UserViewSet(WagtailUserViewSet):
    create_template_name = "wagtailusers/users/create.html"
    edit_template_name = "wagtailusers/users/edit.html"
    edit_view_class = CustomUserEditView

    def get_form_class(self, for_update=False):
        if for_update:
            return CustomUserEditForm
        return CustomUserCreationForm
