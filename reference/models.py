from django.db import models, IntegrityError
from modelcluster.fields import ParentalKey

from core.models import CommonControlField

from journal.models import Journal
# Create your models here.


class JournalTitle(CommonControlField):
    title = models.TextField(null=True, blank=True)


    def __str__(self):
        return f"{self.title}"