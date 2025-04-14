import csv
import os
import sys

from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from wagtail.admin import messages

from core.libs import chkcsv

from .models import EditorialBoardMember, EditorialBoardMemberFile
from journal.models import Journal
from location.models import Location
from researcher.models import Researcher    
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
        with open(file_path, "r") as csvfile:
            data = csv.DictReader(csvfile, delimiter=";")
            for line, row in enumerate(data):
                given_names = row.get("Nome do membro")
                last_name = row.get("Sobrenome")
                journal = Journal.objects.get(title__icontains=row.get("Periódico"))
                gender = Gender.create_or_update(user=request.user, code=row.get("Gender"), gender="F")
                location = Location.create_or_update(
                    user=request.user,
                    city_name=row.get("institution_city_name"),
                    state_text=row.get("institution_state_text"),
                    state_acronym=row.get("institution_state_acronym"),
                    state_name=row.get("institution_state_name"),
                    country_text=row.get("institution_country_text"),
                    country_acronym=row.get("institution_country_acronym"),
                    country_name=row.get("institution_country_name"),
                )
                researcher = Researcher.create_or_update(
                    user=request.user,
                    given_names=given_names,
                    last_name=last_name,
                    suffix=row.get("Suffix"),
                    declared_name=row.get("declared_person_name"),
                    lattes=row.get("CV Lattes"),
                    orcid=row.get("ORCID iD"),
                    email=row.get("Email"),
                    gender=gender,
                    location=location,
                    aff_div1=row.get("institution_div1"),
                    aff_div2=row.get("institution_div2"),
                    aff_name=row.get("Instituição"),
                )
                EditorialBoardMember.create_or_update(
                    user=request.user,
                    researcher=researcher,
                    journal=journal,
                    declared_role=row["Cargo / instância do membro"],
                    std_role=None,
                    editorial_board_initial_year=row["Data"],
                    editorial_board_final_year=row["Data"],
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
