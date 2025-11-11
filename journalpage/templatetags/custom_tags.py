from django import template

register = template.Library()

@register.filter
def dict_key(d, key):
    return d.get(key, {})

@register.filter
def ensure_protocol(url):
    if not url:
        return ''
    if not url.startswith(('http://', 'https://')):
        return f'http://{url}'
    return url