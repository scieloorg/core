from django import template
from search.choices import translates

register = template.Library()


@register.filter
def translate_data(value):
    """
    Returns value or it's verbose version.
    choices is a dict.
    Usage::
        {% load translate %}
        {{data|translate}}
    """

    return translates.get(value, value)