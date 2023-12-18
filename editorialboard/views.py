import csv
import os
from datetime import datetime

from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from wagtail.admin import messages

from core.libs import chkcsv

from .models import EditorialBoardMember, EditorialBoardMemberFile


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
                given_names = row["Nome do membro"]
                last_name = row["Sobrenome"]
                # ed = EditorialBoardMember()
                # ed.get_or_create(
                #     row["Periódico"],
                #     row["Cargo / instância do membro"],
                #     row["Data"],
                #     row["Email"],
                #     row["Institution"],
                #     given_names,
                #     last_name,
                #     row["Suffix"],
                #     row["ORCID iD"],
                #     row["CV Lattes"],
                #     row["Gender"],
                #     row["Gender status"],
                #     request.user,
                # )
                # ,User)

                EditorialBoardMember.create_or_update(
                    request.user,
                    researcher=None,
                    journal=None,
                    journal_title=row["Periódico"],
                    given_names=given_names,
                    last_name=last_name,
                    suffix=row["Suffix"],
                    declared_person_name=row.get("declared_person_name"),
                    lattes=row["CV Lattes"],
                    orcid=row["ORCID iD"],
                    email=row["Email"],
                    gender_code=row["Gender"],
                    gender_identification_status=row["Gender status"],
                    institution_name=row["Institution"],
                    institution_div1=row.get("institution_div1"),
                    institution_div2=row.get("institution_div2"),
                    institution_city_name=row.get("institution_city_name"),
                    institution_country_text=row.get("institution_country_text"),
                    institution_country_acronym=row.get("institution_country_acronym"),
                    institution_country_name=row.get("institution_country_name"),
                    institution_state_text=row.get("institution_state_text"),
                    institution_state_acronym=row.get("institution_state_acronym"),
                    institution_state_name=row.get("institution_state_name"),
                    declared_role=row["Cargo / instância do membro"],
                    std_role=None,
                    member_activity_initial_year=row["Data"],
                    member_activity_final_year=row["Data"],
                    member_activity_initial_month="01",
                    member_activity_final_month="12",
                    editorial_board_initial_year=row["Data"],
                    editorial_board_final_year=row["Data"],
                )
    except Exception as ex:
        messages.error(request, _("Import error: %s, Line: %s") % (ex, str(line + 2)))
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))
