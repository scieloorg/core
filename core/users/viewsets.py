from wagtail.users.views.users import UserViewSet as WagtailUserViewSet

from .forms import CustomUserCreationForm, CustomUserEditForm


class UserViewSet(WagtailUserViewSet):
    create_template_name = "wagtailusers/users/create.html"
    edit_template_name = "wagtailusers/users/edit.html"

    def get_form_class(self, for_update=False):
        if for_update:
            return CustomUserEditForm
        return CustomUserCreationForm
