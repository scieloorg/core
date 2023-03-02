import logging
import os

from django.contrib.auth import get_user_model

from altmetric.altmetric import altmetric
from config import celery_app

User = get_user_model()


@celery_app.task()
def load_altmetric(user_id, file_path):
    """
    Load the data from Altmetric files.

    Sync or Async function

    Param file_path: String with the path of the JSON like file compressed or not.
    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=user_id)

    try:
        for file in os.listdir(file_path):
            logging.info("list_dir : %s/%s" % (file_path, file))
            altmetric.load(file_path, file, user)
    except Exception as e:
        logging.info(e)
