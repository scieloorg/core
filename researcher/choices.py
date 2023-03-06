from django.utils.translation import gettext_lazy as _

GENDER = [("F", _("Mujer")), ("M", _("Hombre"))]

GENDER_IDENTIFICATION_STATUS = [
    ("DECLARED", _("Declarado por el investigador")),
    ("AUTOMATIC", _("Identificado automáticamente por programa de computador")),
    ("MANUAL", _("Identificado por algun usuario")),
]
