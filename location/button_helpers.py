from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail_modeladmin.helpers import ButtonHelper


class CountryHelper(ButtonHelper):
    validate_button_classnames = [
        "button-small",
        "icon",
    ]
    import_button_classnames = [
        "button-small",
        "icon",
    ]

    def validate_button(self, obj):
        text = _("Validate")
        return {
            "url": reverse("validate_country")
            + "?file_id="
            + str(obj.id),  # decide where the button links to
            "label": text,
            "classname": self.finalise_classname(self.validate_button_classnames),
            "title": text,
        }

    def import_button(self, obj):
        # Define a label for our button
        text = _("Import")
        return {
            "url": reverse("import_file_country")
            + "?file_id="
            + str(obj.id),  # decide where the button links to
            "label": text,
            "classname": self.finalise_classname(self.import_button_classnames),
            "title": text,
        }

    def get_buttons_for_obj(
        self, obj, exclude=None, classnames_add=None, classnames_exclude=None
    ):
        btns = super().get_buttons_for_obj(
            obj, exclude, classnames_add, classnames_exclude
        )
        if "validate" not in (exclude or []):
            btns.append(self.validate_button(obj))
        if "import" not in (exclude or []):
            btns.append(self.import_button(obj))
        return btns
