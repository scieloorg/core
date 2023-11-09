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
                ed = EditorialBoardMember()
                ed.get_or_create(
                    row["Periódico"],
                    row["Cargo / instância do membro"],
                    row["Data"],
                    row["Email"],
                    row["Institution"],
                    given_names,
                    last_name,
                    row["Suffix"],
                    row["ORCID iD"],
                    row["CV Lattes"],
                    row["Gender"],
                    row["Gender status"],
                    request.user,
                )
                # ,User)
    except Exception as ex:
        messages.error(request, _("Import error: %s, Line: %s") % (ex, str(line + 2)))
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))
