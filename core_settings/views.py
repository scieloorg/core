import csv
import uuid

from django.http import JsonResponse
from django.utils.translation import gettext as _

from config.settings.base import MODEL_TO_IMPORT_CSV

from .tasks import importar_csv_task


def validate_columns_csv(columns, type_csv):
    required = MODEL_TO_IMPORT_CSV.get(type_csv)
    columns = {item.strip().lower() for item in columns}
    if not required.issubset(columns):
        return JsonResponse(
            {
                "status": False,
                "message": _("Colunas faltando. Colunas requeridas") + f": {sorted(required)}. (Delimitador ;)",  
            }
        )


def validate_type_csv(csv_file):
    if not csv_file.name.endswith(".csv"):
        return JsonResponse(
            {
                "status": False,
                "message": _("Arquivo inválido. Por favor, envie um arquivo CSV."),
            }
        )

    if csv_file.content_type not in ["text/csv", "application/vnd.ms-excel"]:
        return JsonResponse(
            {"status": False, "message": _("O arquivo enviado não é um CSV válido.")}
        )


def import_csv(request):
    if (
        not request.user.is_authenticated or
        not (request.user.is_superuser or request.user.groups.filter(name="Collection Team").exists())
    ):
        return JsonResponse(
            {
                "status": False,
                "message": _("Usuário sem permissão para esta funcionalidade."),
            }
        )

    elif (
        request.method == "POST"
        and request.FILES.get("csv_file")
        and request.POST.get("type_csv")
        in MODEL_TO_IMPORT_CSV
    ):
        username = request.user.username
        csv_file = request.FILES["csv_file"]
        response = validate_type_csv(csv_file)
        type_csv = request.POST.get("type_csv")
        if response:
            return response

        tmp_path = f"/tmp/{uuid.uuid4()}.csv"

        with open(tmp_path, "wb+") as destination:
            for chunk in csv_file.chunks():
                destination.write(chunk)

        with open(tmp_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            csv_columns = set(reader.fieldnames or [])
            response = validate_columns_csv(csv_columns, type_csv) 
            if response:
                return response
        importar_csv_task.apply_async(kwargs=dict(username=username, tmp_path=tmp_path, type_csv=type_csv))

        return JsonResponse(
            {
                "status": True,
                "message": _("CSV importado com sucesso! Realizando importação..."),
            }
        )
    return JsonResponse({"status": False, "message": _("Requisição inválida.")})
