import logging
import sys

from django.contrib.auth import get_user_model

from bigbang.tasks_scheduler import schedule_tasks
from bigbang.utils.scheduler import schedule_task
from collection.models import Collection
from config import celery_app
from core.models import Gender, Language, License
from editorialboard.models import RoleModel
from institution.models import Institution, InstitutionType
from journal.models import (
    DigitalPreservationAgency,
    IndexedAt,
    Standard,
    Subject,
    WebOfKnowledge,
    WebOfKnowledgeSubjectCategory,
)
from location.models import City, Country, State
from thematic_areas.models import ThematicArea
from tracker.models import UnexpectedEvent
from vocabulary.models import Vocabulary

User = get_user_model()


def _get_user(user_id, username):
    if user_id:
        return User.objects.get(pk=user_id)
    if username:
        return User.objects.get(username=username)


@celery_app.task(bind=True)
def task_start(
    self,
    user_id=None,
    username=None,
):
    try:
        user = _get_user(user_id, username)
        Language.load(user)
        Collection.load(user)
        Vocabulary.load(user)
        Standard.load(user)
        Subject.load(user)
        WebOfKnowledge.load(user)
        Country.load(user)
        State.load(user)
        City.load(user)
        ThematicArea.load(user)
        WebOfKnowledgeSubjectCategory.load(user)
        IndexedAt.load(user)
        Institution.load(user)
        RoleModel.load(user)
        License.load(user)
        DigitalPreservationAgency.load(user)
        InstitutionType.load(user)
        Gender.load(user)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "bigbang.tasks.task_start",
            },
        )


@celery_app.task(bind=True)
def task_create_tasks(self, user_id=None, username=None, tasks_data=None):
    if not task_data:
        user = _get_user(user_id, username)
        return schedule_tasks(user)
    for task_data in tasks_data:
        # {
        #     'task': 'pid_provider.tasks.provide_pid_for_am_xmls',
        #     'name': 'provide_pid_for_am_xmls',
        #     'kwargs': {'username': 'adm'},
        #     'description': 'Atribui pid para os artigos provenientes do AM',
        #     'priority': 1,
        #     'enabled': True,
        #     'run_once': False,
        #     'day_of_week': '4',
        #     'hour': '2',
        #     'minute': '1'},
        try:
            schedule_task(**task_data)
        except Exception as e:
            logging.exception(e)
