from django.urls import path

from .views import task_run

app_name = "django_celery_beat"
urlpatterns = [
    path("", view=task_run, name="task_run"),
]
