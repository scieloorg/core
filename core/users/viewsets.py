from wagtail.users.views.users import UserViewSet as WagtailUserViewSet

from .forms import CustomUserCreationForm, CustomUserEditForm
from .views import CustomUserEditView


class UserViewSet(WagtailUserViewSet):
    create_template_name = "wagtailusers/users/create.html"
    edit_template_name = "wagtailusers/users/edit.html"
    edit_view_class = CustomUserEditView

    def get_form_class(self, for_update=False):
        if for_update:
            return CustomUserEditForm
        return CustomUserCreationForm
