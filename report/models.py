import os
import hashlib

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from journal.models import Journal

def csv_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    subdir = "csv_report_article"
    path_parts = [
        subdir,
        instance.journal.title,
        instance.title,
        str(instance.publication_year),
    ]
    filename_hash = hashlib.sha256(filename.encode()).hexdigest()[:10]
    path_parts.append(f"{filename_hash}.csv")
    return os.path.join(*path_parts)


class ReportCSV(CommonControlField):
    journal = models.ForeignKey(
        Journal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    title = models.TextField(
        verbose_name=_("Title"),
        blank=True,
        null=True,
        help_text=_("Complete with the type of report")
    )
    file = models.FileField(
        null=True,
        blank=True,
        verbose_name=_("File"),
        upload_to=csv_directory_path,
    )
    columns = models.JSONField(
        verbose_name=_("JSON File"), 
        null=True, 
        blank=True,
    )
    publication_year = models.CharField(
        verbose_name=_("Publication Year"),
        max_length=4,
        blank=True,
        null=True,
    )

    panels = [
        AutocompletePanel("journal"),
        FieldPanel("title"),
        FieldPanel("file", classname="hide-file-section"),
        FieldPanel("columns"),
        FieldPanel("publication_year"),
    ]

    @classmethod
    def create_or_update(
        cls,
        journal,
        publication_year,
        title,
        csv_data,
        columns,
        user,
    ):
        try:
            obj = cls.objects.get(journal=journal, title=title, publication_year=publication_year)
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user
            obj.journal = journal
            obj.title = title
            obj.publication_year = publication_year
            obj.columns = columns
            obj.save()
        obj.file.save("report.csv", csv_data)
        return obj