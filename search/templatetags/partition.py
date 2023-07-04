from django import template

register = template.Library()


@register.filter
def partition(alist, size):
    """
    Returns a partition value of a list

    Always parts of size

    Ex.:  ['1985', 1, '1990', 1]

    Returns: [['1985', 1], ['1990', 1]]

    """

    return [alist[i : i + size] for i in range(0, len(alist), size)]
