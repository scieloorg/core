from django import template
from journal.models import Journal

register = template.Library()


@register.filter(name='get_journals_by_name_institutiton')
def get_journals_by_name_institutiton(value):
    return Journal.objects.filter(publisher__institution__name=value)