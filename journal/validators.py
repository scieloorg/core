from rest_framework.exceptions import ValidationError


def validate_issn(issn):
    if not issn:
        raise ValidationError("ISSN is a required query parameter")


def validate_params(request, *filters):
    """
    Atraves de filters, verifica os paramentros inseridos na url.
    """
    other_params = set(request.query_params.keys()) - {*filters}
    if other_params:
        raise ValidationError(f"Only {filters} parameters are allowed")
