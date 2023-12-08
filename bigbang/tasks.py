import logging

from django.contrib.auth import get_user_model
from config import celery_app
from collection.models import Collection
from core.models import Language
from institution.models import Institution
from location.models import Country, City, State
from journal.models import Standard, Subject, WebOfKnowledge, WebOfKnowledgeSubjectCategory
from vocabulary.models import Vocabulary
from thematic_areas.models import ThematicArea

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
    Institution.load(user)
