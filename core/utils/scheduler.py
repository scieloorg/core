import json
import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from django_celery_beat.models import CrontabSchedule, PeriodicTask

User = get_user_model()


def schedule_task(
    task,
    name,
    kwargs,
    description=None,
    priority=None,
    enabled=None,
    run_once=None,
    day_of_week=None,
    hour=None,
    minute=None,
):
    """
    Agenda tarefa

    name = nome que é apresentado na lista de tarefas
    task = nome da função
    """
    try:
        periodic_task = PeriodicTask.objects.get(name=name)
    except PeriodicTask.DoesNotExist:
        periodic_task = PeriodicTask()
        periodic_task.name = name
        periodic_task.task = task
    periodic_task.description = description

    if hour is None:
        hour = "*"
    if minute is None:
        minute = "*"
    crontab_schedule, status = CrontabSchedule.objects.get_or_create(
        day_of_week=day_of_week or "*",
        hour=hour,
        minute=minute,
    )
    # kwargs["full"] = bool(full)
    periodic_task.kwargs = json.dumps(kwargs)
    periodic_task.priority = priority or 3
    periodic_task.crontab = crontab_schedule

    full = kwargs.get("full")
    if full:
        periodic_task.enabled = enabled
        periodic_task.one_off = run_once
    else:
        periodic_task.enabled = True
        periodic_task.one_off = False

    periodic_task.save()
    logging.info(_("Scheduled task: {}").format(name))
