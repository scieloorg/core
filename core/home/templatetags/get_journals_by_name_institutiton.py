from django import template
from journal.models import Journal

register = template.Library()


@register.filter(name='get_journals_by_name_institutiton')
def get_journals_by_name_institutiton(value):
    if value:
        return Journal.objects.filter(publisher_history__institution__institution__institution_identification__name__icontains=value)