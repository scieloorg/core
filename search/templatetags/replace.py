from django import template

register = template.Library()


@register.filter(name="replace")
def replace(value):
    return value.replace("-", " ")
