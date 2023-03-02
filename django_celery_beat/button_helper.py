from django.urls import reverse
from django.utils.translation import gettext as _
from wagtail.contrib.modeladmin.helpers import ButtonHelper


class PeriodicTaskHelper(ButtonHelper):
    # Define classes for our button, here we can set an icon for example
    run_button_classnames = [
        "button-small",
        "icon",
    ]

    def run_button(self, obj):
        # Define a label for our button
        text = _("Run")
        return {
            "url": reverse("django_celery_beat:task_run") + "?task_id=%s" % str(obj.id),
            "label": text,
            "classname": self.finalise_classname(self.run_button_classnames),
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
        if "run" not in (exclude or []):
            btns.append(self.run_button(obj))

        return btns
