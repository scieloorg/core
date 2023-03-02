from celery import current_app
from celery.utils import cached_property
from django import forms
from django.forms.widgets import Select
from django.utils.translation import gettext_lazy as _
from kombu.utils.json import loads
from wagtail.admin.forms import WagtailAdminModelForm


class TaskSelectWidget(Select):
    """Widget that lets you choose between task names."""

    celery_app = current_app
    _choices = None

    def tasks_as_choices(self):
        _ = self._modules  # noqa
        tasks = list(
            sorted(
                name for name in self.celery_app.tasks if not name.startswith("celery.")
            )
        )
        return (("", ""),) + tuple(zip(tasks, tasks))

    @property
    def choices(self):
        if self._choices is None:
            self._choices = self.tasks_as_choices()
        return self._choices

    @choices.setter
    def choices(self, _):
        # ChoiceField.__init__ sets ``self.choices = choices``
        # which would override ours.
        pass

    @cached_property
    def _modules(self):
        self.celery_app.loader.import_default_modules()


class TaskChoiceField(forms.ChoiceField):
    """Field that lets you choose between task names."""

    widget = TaskSelectWidget

    def valid_value(self, value):
        return True


class PeriodicTaskForm(WagtailAdminModelForm):
    """Form that lets you create and modify periodic tasks."""

    regtask = TaskChoiceField(
        label=_("Task (registered)"),
        required=False,
    )
    task = forms.CharField(
        label=_("Task (custom)"),
        required=False,
        max_length=200,
    )

    class Meta:
        """Form metadata."""

        exclude = ()

    def clean(self):
        data = super().clean()
        regtask = data.get("regtask")
        if regtask:
            data["task"] = regtask
        if not data["task"]:
            exc = forms.ValidationError(_("Need name of task"))
            self._errors["task"] = self.error_class(exc.messages)
            raise exc

        if data.get("expire_seconds") is not None and data.get("expires"):
            raise forms.ValidationError(
                _("Only one can be set, in expires and expire_seconds")
            )
        return data

    def _clean_json(self, field):
        value = self.cleaned_data[field]
        try:
            loads(value)
        except ValueError as exc:
            raise forms.ValidationError(
                _("Unable to parse JSON: %s") % exc,
            )
        return value

    def clean_args(self):
        return self._clean_json("args")

    def clean_kwargs(self):
        return self._clean_json("kwargs")
