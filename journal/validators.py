from rest_framework.exceptions import ValidationError

def validate_issn(issn):
    if not issn:
        raise ValidationError("ISSN is a required query parameter")
