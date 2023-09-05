import openpyxl
from ..models import IndexedAt


def run():
    xlsx_file_path = 'journal/fixtures/INDEX_AT.xlsx'
    workbook = openpyxl.load_workbook(xlsx_file_path)

    sheet = workbook['Página4']
    for row in sheet.iter_rows(min_row=2, values_only=True):
        acronym, name, type, URL = row
        obj = IndexedAt.create_or_update(name=name, acronym=acronym, type=type, url=URL)