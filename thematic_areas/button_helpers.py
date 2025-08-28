from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail_modeladmin.helpers import ButtonHelper


class GenericThematicAreaHelper(ButtonHelper):
    # Define classes for our button, here we can set an icon for example
    validate_button_classnames = [
        "button-small",
        "icon",
    ]
    import_button_classnames = [
        "button-small",
        "icon",
    ]

    def validate_button(self, obj):
        # Define a label for our button
        text = _("Validate")
        return {
            "url": reverse("generic_thematic_areas:validate")
            + "?file_id=%s" % str(obj.id),
            "label": text,
            "classname": self.finalise_classname(self.validate_button_classnames),
            "title": "validate_generic",
        }

    def import_button(self, obj):
        # Define a label for our button
        text = _("Import")
        return {
            "url": reverse("generic_thematic_areas:import_file")
            + "?file_id=%s" % str(obj.id),
            "label": text,
            "classname": self.finalise_classname(self.import_button_classnames),
            "title": "import_generic",
        }

    def get_buttons_for_obj(
        self, obj, exclude=None, classnames_add=None, classnames_exclude=None
    ):
        """
        This function is used to gather all available buttons.
        We append our custom button to the btns list.
        """
        btns = super().get_buttons_for_obj(
            obj, exclude, classnames_add, classnames_exclude
        )
        if "validate_generic" not in (exclude or []):
            btns.append(self.validate_button(obj))
        if "import_generic" not in (exclude or []):
            btns.append(self.import_button(obj))
        return btns


class ThematicAreaHelper(ButtonHelper):
    # Define classes for our button, here we can set an icon for example
    validate_button_classnames = [
        "button-small",
        "icon",
    ]
    import_button_classnames = [
        "button-small",
        "icon",
    ]

    def validate_button(self, obj):
        # Define a label for our button
        text = _("Validate")
        return {
            "url": reverse("thematic_areas:validate") + "?file_id=%s" % str(obj.id),
            "label": text,
            "classname": self.finalise_classname(self.validate_button_classnames),
            "title": text,
        }

    def import_button(self, obj):
        # Define a label for our button
        text = _("Import")
        return {
            "url": reverse("thematic_areas:import_file") + "?file_id=%s" % str(obj.id),
            "label": text,
            "classname": self.finalise_classname(self.import_button_classnames),
            "title": text,
        }

    def get_buttons_for_obj(
        self, obj, exclude=None, classnames_add=None, classnames_exclude=None
    ):
        """
        This function is used to gather all available buttons.
        We append our custom button to the btns list.
        """
        btns = super().get_buttons_for_obj(
            obj, exclude, classnames_add, classnames_exclude
        )
        if "validate" not in (exclude or []):
            btns.append(self.validate_button(obj))
        if "import" not in (exclude or []):
            btns.append(self.import_button(obj))
        return btns
