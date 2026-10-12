import csv
import os
import sys
from datetime import date

from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from wagtail.admin import messages

from core.libs import chkcsv

from .models import EditorialBoardMember, EditorialBoardMemberFile
from journal.models import Journal
from location.models import Location
from organization.models import Organization
from researcher.models import NewResearcher, ResearcherOrcid
from tracker.models import UnexpectedEvent
from core.models import Gender


def validate_ebm(request):
    """
    This view function validade a csv file based on a pre definition os the fmt
    file.
    The check_csv_file function check that all of the required columns and data
    are present in the CSV file, and that the data conform to the appropriate
    type and other specifications, when it is not valid return a list with the
    errors.
    """
    errorlist = []
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(EditorialBoardMemberFile, pk=file_id)

    if request.method == "GET":
        try:
            upload_path = file_upload.attachment.file.path
            cols = chkcsv.read_format_specs(
                os.path.dirname(os.path.abspath(__file__)) + "/chkcsvfmt.fmt",
                True,
                False,
            )
            errorlist = chkcsv.check_csv_file(
                upload_path, cols, True, True, True, False
            )
            if errorlist:
                raise Exception(_("Validation error"))
            else:
                file_upload.is_valid = True
                fp = open(upload_path)
                file_upload.line_count = len(fp.readlines())
                file_upload.save()
        except Exception as ex:
            messages.error(request, _("Validation error: %s") % errorlist)
        else:
            messages.success(request, _("File successfully validated!"))

    return redirect(request.META.get("HTTP_REFERER"))


def import_file_ebm(request):
    """
    This view function import the data from a CSV file.
    Something like this:
        Acronym;Name;Type;URL;Description
    """
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(EditorialBoardMemberFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    try:
        user = request.user
        with open(file_path, "r") as csvfile:
            data = csv.DictReader(csvfile, delimiter=";")
            for line, row in enumerate(data):
                given_names = row.get("Nome do membro")
                last_name = row.get("Sobrenome")
                journal = Journal.objects.get(title__icontains=row.get("Periódico"))
                gender = Gender.create_or_update(user=user, code=row.get("Gender"), gender="F")
                location = Location.create_or_update(
                    user=user,
                    city_name=row.get("institution_city_name"),
                    state_text=row.get("institution_state_text"),
                    state_acronym=row.get("institution_state_acronym"),
                    state_name=row.get("institution_state_name"),
                    country_text=row.get("institution_country_text"),
                    country_acronym=row.get("institution_country_acronym"),
                    country_name=row.get("institution_country_name"),
                )
                affiliation = None
                if row.get("Instituição"):
                    affiliation = Organization.create_or_update(
                        user=user,
                        name=row.get("Instituição"),
                        location=location,
                    )
                orcid = None
                if row.get("ORCID iD"):
                    orcid = ResearcherOrcid.get_or_create(
                        user=user, orcid=row.get("ORCID iD")
                    )
                researcher = NewResearcher.get_or_create(
                    user=user,
                    given_names=given_names,
                    last_name=last_name,
                    suffix=row.get("Suffix"),
                    affiliation=affiliation,
                    orcid=orcid,
                    gender=gender,
                )
                researcher.add_lattes_id(row.get("CV Lattes"), user)
                researcher.add_email(row.get("Email"), user)

                year = date(int(row["Data"]), 1, 1)
                EditorialBoardMember.create_or_update(
                    user=user,
                    researcher=researcher,
                    journal=journal,
                    declared_role=row["Cargo / instância do membro"],
                    std_role=None,
                    editorial_board_initial_year=year,
                    editorial_board_final_year=year,
                )

    except Exception as ex:
        messages.error(request, _("Import error: %s, Line: %s. Exception: %s") % (ex, str(line + 2), ex))
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            item=str(file_upload),
            action="editorialboard.views.import_file_ebm",
            exception=ex,
            exc_traceback=exc_traceback,
            detail=dict(
                line=line,
                row=row,
                file_path=file_path,
                file_id=file_id,
            ),
        )
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))
