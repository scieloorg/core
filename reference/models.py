from django.db import models, IntegrityError
from modelcluster.fields import ParentalKey

from core.models import CommonControlField

from journal.models import Journal
# Create your models here.


class JournalTitle(CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="other_titles", null=True
    )
    title = models.TextField(null=True, blank=True)


    class Meta:
        unique_together = [("journal", "title")]


    @classmethod
    def get(
        cls,
        title,
        journal,
    ):
        if not title and not journal:
            raise ValueError("JournalTitle.get requires title paramenter")
        return journal.other_titles.get(title=title)
        
    @classmethod
    def create(
        cls,
        title,
        journal,
        user,
    ):
        try:
            obj = cls(
                title=title,
                journal=journal,
                creator=user,
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(title=title, journal=journal)

    @classmethod
    def create_or_update(
        cls,
        title,
        journal,
        user,
    ):
        try:
            return cls.get(title=title, journal=journal)
        except cls.DoesNotExist:
            return cls.create(title=title, journal=journal, user=user)
    
    def __str__(self):
        return f"{self.title}"
