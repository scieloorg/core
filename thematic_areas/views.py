import csv
import os
from datetime import datetime

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from wagtail.admin import messages

from core.libs import chkcsv

from .models import (
    GenericThematicArea,
    GenericThematicAreaFile,
    ThematicArea,
    ThematicAreaFile,
)


def generic_validate(request):
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
        file_upload = get_object_or_404(GenericThematicAreaFile, pk=file_id)

    if request.method == "GET":
        try:
            upload_path = file_upload.attachment.file.path
            cols = chkcsv.read_format_specs(
                os.path.dirname(os.path.abspath(__file__)) + "/generic_chkcsvfmt.fmt",
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


def generic_import_file(request):
    """
    This view function import the data from a CSV file.

    Something like this:

    text;lang;origin;level;level_up
    Álgebra;pt;CAPES;3;Matemática
    Matemática;pt;CAPES;2;Ciências Exatas e da Terra
    Ciências Exatas e da Terra;pt;CAPES;1;Ciências Físicas, Tecnológicas e Multidisciplinares
    Ciências Físicas, Tecnológicas e Multidisciplinares;pt;CAPES;0;

    TODO: This function must be a task.
    """
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(GenericThematicAreaFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    with open(file_path, "r") as csvfile:
        data = csv.DictReader(csvfile, delimiter=";")

        for line, row in enumerate(data):
            try:
                the_area = GenericThematicArea()
                the_area.text = row.get("text")
                the_area.lang = row.get("lang")
                the_area.origin = row.get("origin")
                the_area.level = row.get("level")
                the_area.creator = request.user
                the_area.save()
            except Exception as ex:
                messages.error(request, _("Import error: %(exception)s, Line: %(line)s") % {'exception': ex, 'line': str(line + 2)})
        else:
            messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))


def generic_download_sample(request):
    """
    This view function a CSV sample for model ThematicAreaFile.
    """
    file_path = (
        os.path.dirname(os.path.abspath(__file__)) + "/fixtures_thematic_areas.csv"
    )
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="text/csv")
            response["Content-Disposition"] = "inline; filename=" + os.path.basename(
                file_path
            )
            return response
    raise Http404


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
        file_upload = get_object_or_404(ThematicAreaFile, pk=file_id)

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


def import_file(request):
    """
    This view function import the data from a CSV file.

    Something like this:

        Title,Institution,Link,Description,date
        Politica de acesso aberto,Instituição X,http://www.ac.com.br,Diretório internacional de política de acesso aberto

    TODO: This function must be a task.
    """
    file_id = request.GET.get("file_id", None)

    if file_id:
        file_upload = get_object_or_404(ThematicAreaFile, pk=file_id)

    file_path = file_upload.attachment.file.path

    try:
        with open(file_path, "r") as csvfile:
            data = csv.DictReader(csvfile, delimiter=";")

            for line, row in enumerate(data):
                ta = ThematicArea()
                ta.level0 = row["ThematicAreaLevel0"]
                ta.level0 = row["ThematicAreaLevel1"]
                ta.level0 = row["ThematicAreaLevel2"]
                ta.creator = request.user
                ta.save()

    except Exception as ex:
        messages.error(request, _("Import error: %(exception)s, Line: %(line)s") % {'exception': ex, 'line': str(line + 2)})
    else:
        messages.success(request, _("File imported successfully!"))

    return redirect(request.META.get("HTTP_REFERER"))


def download_sample(request):
    """
    This view function a CSV sample for model ThematicAreaFile.
    """
    file_path = (
        os.path.dirname(os.path.abspath(__file__)) + "/fixtures_thematic_areas.csv"
    )
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="text/csv")
            response["Content-Disposition"] = "inline; filename=" + os.path.basename(
                file_path
            )
            return response
    raise Http404
