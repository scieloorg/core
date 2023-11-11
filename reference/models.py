from django.db import models
from core.models import CommonControlField

# Create your models here.


class JournalTitle(CommonControlField):
    title = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.title}"
