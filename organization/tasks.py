import sys

from django.apps import apps
from django.contrib.auth import get_user_model

from .models import Organization
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
    model_cls = apps.get_model("journal", model)
    objects = model_cls.objects.select_related(
        "institution__institution__location",
        "institution__institution__institution_identification",
    ).filter(
        institution__institution__institution_identification__is_official=True,
        institution__institution__location__city__isnull=False,
        institution__institution__location__country__isnull=False,
    )
    for obj in objects:
        institution_data = obj.institution.institution.data
        institution_data["location_id"] = obj.institution.institution.location.id

        task_children_migrate_data.apply_async(
            kwargs={
                "user_id": user_id,
                "username": username,
                "model_institutition": obj.__class__.__name__,
                "model_institutition_id": obj.id,
                "institution_data": institution_data,
            }
        )


@celery_app.task()
def task_children_migrate_data(
    user_id,
    username,
    model_institutition,
    model_institutition_id,
    institution_data,
):
    user = _get_user(request=None, user_id=user_id, username=username)

    try:
        location = Location.objects.get(id=institution_data.get("location_id"))
        model_org_level = apps.get_model(
            "organization", f"OrgLevel{model_institutition}"
        )
        model_institutition = apps.get_model("journal", model_institutition)
        obj_institution = model_institutition.objects.get(id=model_institutition_id)

        try:
            org_type = OrganizationInstitutionType.create_or_update(
                user=user,
                name=institution_data.get("institution__type_scielo"),
            )
        except OrganizationTypeGetError:
            org_type = None

        obj_organization = Organization.create_or_update(
            user=user,
            name=institution_data.get("institution__name"),
            acronym=institution_data.get("institution__acronym"),
            url=institution_data.get("institution__url"),
            institution_type_mec=institution_data.get("institution__type"),
            institution_type_scielo=org_type,
            is_official=institution_data.get("institution__is_official"),
            location=location,
        )

        model_org_level.create_or_update(
            user=user,
            organization=obj_institution,
            level_1=institution_data.get("institution__level_1"),
            level_2=institution_data.get("institution__level_2"),
            level_3=institution_data.get("institution__level_3"),
        )

        obj_institution.organization = obj_organization
        obj_institution.save()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "organization.tasks.task_children_migrate_data",
                "model_institutition": model_institutition,
                "model_institutition_id": model_institutition_id,
                "institution_data": institution_data,
            },
        )
