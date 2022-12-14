from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app

from collection import controller


User = get_user_model()


@celery_app.task(name=_("Carga de metadados de coleções"))
def task_load_collection(*args):
    user_id = args[0] if args else 1

    user = User.objects.get(id=user_id)

    controller.load(user)
