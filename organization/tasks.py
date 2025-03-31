import sys

from django.apps import apps
from django.contrib.auth import get_user_model

from .exceptions import OrganizationTypeGetError
from core.utils.utils import _get_user
from config import celery_app
from location.models import Location
from tracker.models import UnexpectedEvent
from organization.models import OrganizationInstitutionType

User = get_user_model()


@celery_app.task()
def task_migrate_date_institution_to_organization_publisher(
    user_id, username, model, collection, journal
):
    model = apps.get_model("institution", model)
    objects = model.objects.all()
    for obj in objects:
        task_children_migrate_data.apply_async(
            user_id=user_id,
            username=username,
            model=obj.__class__.__name__,
            location_id=obj.institution.location.id,
            **obj.institution.data,
        )


@celery_app.task()
def task_children_migrate_data(
    user_id, 
    username, 
    model, 
    location_id, 
    institution__type_scielo,
    institution__name,
    institution__acronym,
    institution__url,
    institution__type,
    institution__level_1,
    institution__level_2,
    institution__level_3,
    institution__is_official,
    
    ):
    user = _get_user(request=None, user_id=user_id, username=username)
    location = Location.objects.get(id=location_id)
    
    try:
        org_type = OrganizationInstitutionType.create_or_update(
            user=user,
            name=institution__type_scielo,
        )
    except OrganizationTypeGetError:
        org_type = None


    model = apps.get_model("organization", f"Organization{model}")
    model.create_or_update(
        user=user,
        name=institution__name,
        acronym=institution__acronym,
        url=institution__url,
        institution_type_mec=institution__type,
        institution_type_scielo=org_type,
        level_1=institution__level_1,
        level_2=institution__level_2,
        level_3=institution__level_3,
        is_official=institution__is_official,
        location=location,
    )
