from django.utils.translation import gettext_lazy as _

GENDER_IDENTIFICATION_STATUS = [
    ("DECLARED", _("Declarado por el investigador")),
    ("AUTOMATIC", _("Identificado automáticamente por programa de computador")),
    ("MANUAL", _("Identificado por algun usuario")),
]

ROLE = [
    ("Editor-Chefe", _("Editor-Chefe")),
    ("Editor(es) Executivo", _("Editor(es) Executivo")),
    ("Editor(es) Associados ou de Seção", _("Editor(es) Associados ou de Seção")),
    ("Equipe Técnica", _("Equipe Técnica")),
]

