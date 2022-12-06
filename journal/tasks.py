from config import celery_app

from . import controller


@celery_app.task()
def create_kbart():
    """
    Create a journals kbart file in fixtures
    Sync or Async function
    """
    controller.create_journals_kbart()
