import logging

from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from wagtail.users.forms import UserCreationForm, UserEditForm

from collection.models import Collection
from config.settings.base import COLLECTION_TEAM, JOURNAL_TEAM
from journal.models import Journal

User = get_user_model()


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User

        error_messages = {
            "username": {"unique": _("This username has already been taken.")}
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


def validate_journals_belong_to_collections(journals, collections):
    """
    Validates that all selected journals belong to at least one of the selected collections.

    Args:
        journals: QuerySet of selected journals
        collections: QuerySet of selected collections

    Returns:
        True if all journals belong to at least one collection, False otherwise
    """
    if not journals or not collections:
        return False

    for journal in journals:
        if not journal.scielojournal_set.filter(collection__in=collections).exists():
            return False
    return True


class CustomUserFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_collection_field_requirement()

    def _setup_collection_field_requirement(self):
        instance_is_super = getattr(self.instance, "is_superuser", False)
        if instance_is_super and "collection" in self.fields:
            logging.info("User is superuser, setting collection field to not required.")
            self.fields["collection"].required = False
            return True

    def _get_groups_name(self, groups):
        """extracts the names of the groups from the queryset."""
        if not groups:
            return set()
        return set(groups.values_list("name", flat=True))

    def _validate_group_exclusivity(self, groups_names):
        """Ensures that 'Collection Team' and 'Journal Team' are not selected together."""
        if COLLECTION_TEAM in groups_names and JOURNAL_TEAM in groups_names:
            raise forms.ValidationError(
                _(
                    "You cannot select both 'Collection Team' and 'Journal Team'. Please select only one."
                )
            )

    def _should_skip_journal_validation(self, cleaned_data, groups_names):
        """Determines if journal validation should be skipped"""
        return self.instance.is_superuser or COLLECTION_TEAM in groups_names

    def _validate_journals_and_collections(self, journals, collections):
        """Validates that journal belong to selected collections."""
        if not validate_journals_belong_to_collections(journals, collections):
            if not journals:
                raise forms.ValidationError(_("Please select at least one journal."))
            raise forms.ValidationError(
                _("Selected journals do not belong to the selected collections.")
            )

    def clean(self):
        """Perform form validation."""
        cleaned_data = super().clean()
        groups = cleaned_data.get("groups")
        journals = cleaned_data.get("journal")
        collections = cleaned_data.get("collection")

        groups_names = self._get_groups_name(groups)
        self._validate_group_exclusivity(groups_names)

        if self._should_skip_journal_validation(cleaned_data, groups_names):
            logging.info(
                "User is superuser or in Collection Team, skipping journal collection validation."
            )
            return cleaned_data

        self._validate_journals_and_collections(journals, collections)
        return cleaned_data


class CustomUserEditForm(CustomUserFormMixin, UserEditForm):
    journal = forms.ModelMultipleChoiceField(
        queryset=Journal.get_journal_queryset_with_active_collections(),
        required=False,
        label=_("Journal"),
        help_text=_("Select journals this user can access."),
    )
    collection = forms.ModelMultipleChoiceField(
        queryset=Collection.objects.filter(is_active=True),
        required=True,
        label=_("Collection"),
        help_text=_("Select collections this user can access."),
    )

    class Meta(UserEditForm.Meta):
        fields = UserEditForm.Meta.fields | {"journal", "collection"}


class CustomUserCreationForm(CustomUserFormMixin, UserCreationForm):
    journal = forms.ModelMultipleChoiceField(
        queryset=Journal.get_journal_queryset_with_active_collections(),
        required=False,
        label=_("Journal"),
        help_text=_("Select journals this user can access."),
    )
    collection = forms.ModelMultipleChoiceField(
        queryset=Collection.objects.filter(is_active=True),
        required=True,
        label=_("Collection"),
        help_text=_("Select collections this user can access."),
    )

    class Meta(UserEditForm.Meta):
        fields = UserCreationForm.Meta.fields | {"journal", "collection"}
