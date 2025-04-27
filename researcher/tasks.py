import sys

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from wagtail.images.models import Image

from collection.models import Collection
from config import celery_app
from core.utils.utils import _get_user, fetch_data
from location.models import Location
from researcher.models import Researcher, NewResearcher, ResearcherIds
from organization.models import Organization
from tracker.models import UnexpectedEvent

User = get_user_model()


@celery_app.task
def migrate_old_researcher_to_new_researcher(username=None, user_id=None):
    old_researchers = Researcher.objects.filter(
        researcheraka__researcher_identifier__source_name="ORCID",
        researcheraka__researcher_identifier__identifier__isnull=False,
    ).select_related(
        "person_name",
        "affiliation__institution__institution_identification",
    )
    for old_researcher in old_researchers:
        orcid = (
            old_researcher.researcheraka_set.filter(
                researcher_identifier__source_name__iexact="ORCID"
            )
            .first()
            .researcher_identifier.identifier
        )
        data = dict(
            given_names=old_researcher.person_name.given_names,
            last_name=old_researcher.person_name.last_name,
            declared_name=old_researcher.person_name.declared_name,
            suffix=old_researcher.person_name.suffix,
            orcid=orcid,
            source_name="ORCID",
            affiliation_name=old_researcher.affiliation.institution.institution_identification.name,
            affiliation_acronym=old_researcher.affiliation.institution.institution_identification.acronym,
            affiliation_is_official=old_researcher.affiliation.institution.institution_identification.is_official,
            institution_type=old_researcher.affiliation.institution.institution_type,
            institution_url=old_researcher.affiliation.institution.url,
            location_id=old_researcher.affiliation.institution.location.id,
        )
        children_migrate_old_researcher_to_new_researcher.apply_async(
            kwargs=dict(
                username=username,
                user_id=user_id,
                data=data,
            )
        )


@celery_app.task
def children_migrate_old_researcher_to_new_researcher(
    username,
    data,
    user_id=None,
):
    user = _get_user(request=None, username=username, user_id=user_id)
    location = Location.objects.get(id=data.get("location_id"))
    researcher_identifier = ResearcherIds.get_or_create(
        source_name=data.get("source_name"),
        identifier=data.get("orcid"),
        user=user,
    )
    affiliation = Organization.create_or_update(
        name=data.get("affiliation_name"),
        acronym=data.get("affiliation_acronym"),
        is_official=data.get("affiliation_is_official"),
        institution_type_mec=data.get("institution_type"),
        url=data.get("institution_url"),
        location=location,
    )
    NewResearcher.get_or_create(
        user=user,
        given_names=data.get("given_names"),
        last_name=data.get("last_name"),
        suffix=data.get("suffix"),
        researcher_identifier=researcher_identifier,
        affiliation=affiliation,
    )
