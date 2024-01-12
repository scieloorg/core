import csv
import os
from datetime import datetime

from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from wagtail.admin import messages

from core.libs import chkcsv

from .models import Country, CountryFile


# Create your views here.
def validate_country(request):
    errorlist = []
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(CountryFile, pk=file_id)

    if request.method == "GET":
        try:
            upload_path = file_upload.attachment.file.path
            cols = chkcsv.read_format_specs(
                os.path.dirname(os.path.abspath(__file__)) + "/country_chkcsvfmt.fmt",
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


def import_file_country(request):
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(CountryFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    try:
        with open(file_path, "r") as csvfile:
            data = csv.DictReader(csvfile, delimiter=";")

            for line, row in enumerate(data):
                c = Country()
                c.name = row["Country"]
                c.acronym = row["Acronym 2 letters"]
                c.acron3 = row["Acronym 3 letters"]
                c.creator = request.user
                c.save()

    except Exception as ex:
        messages.error(request, _("Import error: %(exception)s, Line: %(line)s") % {'exception': ex, 'line': str(line + 2)})
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))
