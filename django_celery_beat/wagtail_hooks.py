from celery import current_app
from django.conf import settings
from django.contrib import messages
from django.db.models import Case, Value, When
from django.template.defaultfilters import pluralize
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from kombu.utils.json import loads
from wagtail import hooks
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)

from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    PeriodicTasks,
    SolarSchedule,
)
from django_celery_beat.utils import is_database_scheduler

from .button_helper import PeriodicTaskHelper


class PeriodicTaskAdmin(ModelAdmin):
    """Admin-interface for periodic tasks."""

    button_helper_class = PeriodicTaskHelper
    model = PeriodicTask
    menu_icon = "cog"
    celery_app = current_app
    date_hierarchy = "start_time"
    list_display = (
        "__str__",
        "enabled",
        "interval",
        "start_time",
        "last_run_at",
        "one_off",
    )
    list_filter = [
        "enabled",
        "one_off",
        "task",
    ]
    actions = ("enable_tasks", "disable_tasks", "toggle_tasks", "run_tasks")
    search_fields = ("name",)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        scheduler = getattr(settings, "CELERYBEAT_SCHEDULER", None)
        extra_context["wrong_scheduler"] = not is_database_scheduler(scheduler)
        return super(PeriodicTaskAdmin, self).changelist_view(request, extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("interval", "crontab", "solar", "clocked")

    def _message_user_about_update(self, request, rows_updated, verb):
        """Send message about action to user.
        `verb` should shortly describe what have changed (e.g. 'enabled').
        """
        self.message_user(
            request,
            _("{0} task{1} {2} successfully {3}").format(
                rows_updated,
                pluralize(rows_updated),
                pluralize(rows_updated, _("was,were")),
                verb,
            ),
        )

    def enable_tasks(self, request, queryset):
        rows_updated = queryset.update(enabled=True)
        PeriodicTasks.update_changed()
        self._message_user_about_update(request, rows_updated, "enabled")

    enable_tasks.short_description = _("Enable selected tasks")

    def disable_tasks(self, request, queryset):
        rows_updated = queryset.update(enabled=False, last_run_at=None)
        PeriodicTasks.update_changed()
        self._message_user_about_update(request, rows_updated, "disabled")

    disable_tasks.short_description = _("Disable selected tasks")

    def _toggle_tasks_activity(self, queryset):
        return queryset.update(
            enabled=Case(
                When(enabled=True, then=Value(False)),
                default=Value(True),
            )
        )

    def toggle_tasks(self, request, queryset):
        rows_updated = self._toggle_tasks_activity(queryset)
        PeriodicTasks.update_changed()
        self._message_user_about_update(request, rows_updated, "toggled")

    toggle_tasks.short_description = _("Toggle activity of selected tasks")

    def run_tasks(self, request, queryset):
        self.celery_app.loader.import_default_modules()
        tasks = [
            (
                self.celery_app.tasks.get(task.task),
                loads(task.args),
                loads(task.kwargs),
                task.queue,
                task.name,
            )
            for task in queryset
        ]

        if any(t[0] is None for t in tasks):
            for i, t in enumerate(tasks):
                if t[0] is None:
                    break

            # variable "i" will be set because list "tasks" is not empty
            not_found_task_name = queryset[i].task

            self.message_user(
                request,
                _('task "{0}" not found'.format(not_found_task_name)),
                level=messages.ERROR,
            )
            return

        task_ids = [
            task.apply_async(
                args=args,
                kwargs=kwargs,
                queue=queue,
                periodic_task_name=periodic_task_name,
            )
            if queue and len(queue)
            else task.apply_async(
                args=args, kwargs=kwargs, periodic_task_name=periodic_task_name
            )
            for task, args, kwargs, queue, periodic_task_name in tasks
        ]
        tasks_run = len(task_ids)
        self.message_user(
            request,
            _("{0} task{1} {2} successfully run").format(
                tasks_run,
                pluralize(tasks_run),
                pluralize(tasks_run, _("was,were")),
            ),
        )

    run_tasks.short_description = _("Run selected tasks")


class ClockedScheduleAdmin(ModelAdmin):
    """Admin-interface for clocked schedules."""

    menu_icon = "time"
    model = ClockedSchedule

    fields = ("clocked_time",)
    list_display = ("clocked_time",)


class IntervalScheduleAdmin(ModelAdmin):
    """Admin-interface for clocked schedules."""

    menu_icon = "date"
    model = IntervalSchedule


class CrontabScheduleAdmin(ModelAdmin):
    """Admin-interface for clocked schedules."""

    menu_icon = "date"
    model = CrontabSchedule


class SolarScheduleAdmin(ModelAdmin):
    """Admin-interface for clocked schedules."""

    menu_icon = "date"
    model = SolarSchedule


class TasksModelsAdminGroup(ModelAdminGroup):
    menu_label = _("Tasks")
    menu_icon = "cogs"
    menu_order = 1000
    items = (
        PeriodicTaskAdmin,
        CrontabScheduleAdmin,
        IntervalScheduleAdmin,
        ClockedScheduleAdmin,
        SolarScheduleAdmin,
    )


modeladmin_register(TasksModelsAdminGroup)


@hooks.register("register_admin_urls")
def register_task_url():
    return [
        path(
            "django_celery_beat/tasks/",
            include("django_celery_beat.urls", namespace="django_celery_beat"),
        ),
    ]
