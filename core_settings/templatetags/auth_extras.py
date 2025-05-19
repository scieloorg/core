from django import template
from django.contrib.auth.models import Group 
from config.settings.base import MODEL_TO_IMPORT_CSV

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name): 
    return user.groups.filter(name=group_name).exists()

