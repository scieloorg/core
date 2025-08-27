import csv
import os
from datetime import datetime

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from wagtail.admin import messages

from core.libs import chkcsv

from .models import IndexedAt, IndexedAtFile


def validate(request):
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
        file_upload = get_object_or_404(IndexedAtFile, pk=file_id)

    if request.method == "GET":
        try:
            upload_path = file_upload.attachment.file.path
            cols = chkcsv.read_format_specs(
                os.path.dirname(os.path.abspath(__file__)) + "/chkcsvfmt.fmt",
                False,
                False,
            )
            errorlist = chkcsv.check_csv_file(
                upload_path, cols, True, True, True, False
            )
            print(errorlist)
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


def import_file(request):
    """
    This view function import the data from a CSV file.
    Something like this:
        Acronym;Name;Type;URL;Description
    """
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(IndexedAtFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    try:
        with open(file_path, "r") as csvfile:
            data = csv.DictReader(csvfile)

            for line, row in enumerate(data):
                IndexedAt.create_or_update(
                    name=row.get("name"),
                    acronym=row.get("acronym"),
                    url=row.get("URL"),
                    description=row.get("description"),
                    type=row.get("type"),
                    user=request.user,
                )
    except Exception as ex:
        messages.error(
            request,
            _("Import error: %(exception)s, Line: %(line)s")
            % {"exception": ex, "line": str(line + 2)},
        )
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))
