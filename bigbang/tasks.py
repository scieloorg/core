import logging

from django.contrib.auth import get_user_model
from config import celery_app
from collection.models import Collection
from core.models import Language, License
from editorialboard.models import RoleModel
from institution.models import Institution
from location.models import Country, City, State
from journal.models import Standard, Subject, WebOfKnowledge, WebOfKnowledgeSubjectCategory, IndexedAt, DigitalPreservationAgency
from vocabulary.models import Vocabulary
from thematic_areas.models import ThematicArea
from bigbang.utils.scheduler import schedule_task


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


@celery_app.task(bind=True)
def task_create_tasks(self, user_id, tasks_data):
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
