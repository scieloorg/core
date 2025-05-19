import csv
import logging
import sys

from datetime import date
from django.contrib.auth import get_user_model

from config import celery_app
from core.models import Gender
from core.utils.utils import _get_user
from editorialboard.models import EditorialBoardMember
from journal.models import Journal
from location.models import Location
from organization.models import Organization
from researcher.models import NewResearcher, ResearcherIds, ResearcherOrcid
from tracker.models import UnexpectedEvent

User = get_user_model()


@celery_app.task()
def importar_csv_task(username, tmp_path, type_csv):
    if type_csv == "organization":
        return importar_csv_task_organization.apply_async(
            kwargs=dict(tmp_path=tmp_path, username=username)
        )
    elif type_csv == "newresearcher":
        return importar_csv_task_newresearcher.apply_async(
            kwargs=dict(tmp_path=tmp_path, username=username)
        )
    elif type_csv == "editorialboardmember":
        return importar_csv_task_editorialboardmember.apply_async(
            kwargs=dict(tmp_path=tmp_path, username=username)
        )
    else:
        raise ValueError(f"Tipo CSV desconhecido: {type_csv}")


def create_or_update_researcher(
    username,
    country_code,
    city,
    state,
    organization_name,
    acronym,
    url,
    institution_type_mec,
    orcid,
    given_names,
    last_name,
    suffix,
    email,
    lattes,
    gender,
    gender_identification_status,
):
    user = _get_user(request=None, user_id=None, username=username)
    location = Location.create_or_update(
        user=user,
        country_acronym=country_code,
        city_name=city,
        state_text=state,
    )
    affiliation = Organization.create_or_update(
        user=user,
        name=organization_name,
        acronym=acronym,
        location=location,
        url=url,
        institution_type_mec=institution_type_mec,
    )
    orcid = ResearcherOrcid.get_or_create(
        user=user,
        orcid=orcid,
    )
    gender = Gender.create_or_update(user=user, code=gender)
    newresearcher = NewResearcher.get_or_create(
        user=user,
        given_names=given_names,
        last_name=last_name,
        suffix=suffix,
        affiliation=affiliation,
        orcid=orcid,
        gender_identification_status=gender_identification_status,
        gender=gender,
    )
    if lattes:
        researcher_ids = ResearcherIds.get_or_create(
            user=user,
            researcher=newresearcher,
            identifier=lattes,
            source_name="LATTES",
        )
    if email:
        researcher_ids = ResearcherIds.get_or_create(
            user=user,
            researcher=newresearcher,
            identifier=email,
            source_name="EMAIL",
        )
    return newresearcher


def read_csv(tmp_path, delimiter=";"):
    with open(tmp_path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def clean_row(row):
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


@celery_app.task()
def importar_csv_task_organization(tmp_path, username):
    logging.info(f"[importar_csv_task_organization] Importing CSV file: {tmp_path}")
    user = _get_user(request=None, user_id=None, username=username)
    rows = read_csv(tmp_path)
    for i, row in enumerate(rows):
        try:
            row = clean_row(row)
            location = Location.objects.get(
                country__acronym=row.get("country_code"),
                city__name=row.get("city"),
                state__name=row.get("state"),
            )
            organization = Organization.create_or_update(
                user=user,
                name=row.get("organization_name"),
                acronym=row.get("acronym"),
                location=location,
                url=row.get("url"),
                institution_type_mec=row.get("institution_type_mec"),
            )
        except Exception as e:
            logging.exception(f"Linhs {i} com error: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                action="import_csv_organization",
                exc_traceback=exc_traceback,
                detail={
                    "task": "organization.tasks.importar_csv_task_organization",
                    "line": i,
                    "row": row,
                },
            )


@celery_app.task()
def importar_csv_task_newresearcher(tmp_path, username):
    logging.info(f"[importar_csv_task_newresearcher] Importing CSV file: {tmp_path}")
    rows = read_csv(tmp_path)
    for i, row in enumerate(rows):
        try:
            row = clean_row(row)
            create_or_update_researcher(
                username=username,
                country_code=row.get("country_code"),
                city=row.get("city"),
                state=row.get("state"),
                organization_name=row.get("affiliation"),
                acronym=row.get("acronym"),
                url=row.get("url"),
                institution_type_mec=row.get("institution_type_mec"),
                orcid=row.get("orcid"),
                given_names=row.get("given_names"),
                last_name=row.get("last_name"),
                suffix=row.get("suffix"),
                email=row.get("email"),
                lattes=row.get("lattes"),
                gender=row.get("gender"),
                gender_identification_status=row.get("gender_identification_status"),
            )
        except Exception as e:
            logging.exception(f"Linhs {i} com error: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                action="import_csv_newresearcher",
                exc_traceback=exc_traceback,
                detail={
                    "task": "organization.tasks.importar_csv_task_newresearcher",
                    "line": i,
                    "row": row,
                },
            )


@celery_app.task()
def importar_csv_task_editorialboardmember(tmp_path, username):
    logging.info(
        f"[importar_csv_task_editorialboardmember] Importing CSV file: {tmp_path}"
    )
    user = _get_user(request=None, user_id=None, username=username)
    rows = read_csv(tmp_path)
    for i, row in enumerate(rows):
        try:
            row = clean_row(row)
            journal = Journal.objects.get(title__icontains=row.get("title_journal"))
            researcher = create_or_update_researcher(
                username=username,
                country_code=row.get("country_code"),
                city=row.get("city"),
                state=row.get("state"),
                organization_name=row.get("affiliation"),
                acronym=row.get("acronym"),
                url=row.get("url"),
                institution_type_mec=row.get("institution_type_mec"),
                orcid=row.get("orcid"),
                given_names=row.get("given_names"),
                last_name=row.get("last_name"),
                suffix=row.get("suffix"),
                email=row.get("email"),
                lattes=row.get("lattes"),
                gender=row.get("gender"),
                gender_identification_status=row.get("gender_identification_status"),
            )

            initail_year = date(int(row.get("initial_year")), 1, 1)
            final_year = date(int(row.get("final_year")), 1, 1)
            EditorialBoardMember.create_or_update(
                user=user,
                researcher=researcher,
                journal=journal,
                declared_role=row.get("declared_role"),
                std_role=row.get("std_role"),
                editorial_board_initial_year=initail_year,
                editorial_board_final_year=final_year,
            )
        except Exception as e:
            logging.exception(f"Linhs {i} com error: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                action="importar_csv_task_editorialboardmember",
                exc_traceback=exc_traceback,
                detail={
                    "task": "organization.tasks.importar_csv_task_editorialboardmember",
                    "line": i,
                    "row": row,
                },
            )
