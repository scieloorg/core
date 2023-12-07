from django.utils.translation import gettext_lazy as _

GENDER_IDENTIFICATION_STATUS = [
    ("DECLARED", _("Declarado por el investigador")),
    ("AUTOMATIC", _("Identificado automáticamente por programa de computador")),
    ("MANUAL", _("Identificado por algun usuario")),
]

EDITOR_IN_CHIEF = "editor-in-chief"
EXECUTIVE_EDITOR = "executive editor"
ASSOCIATE_EDITOR = "associate editor"
TECHNICAL_TEAM = "technical team"
ROLE = [
    (EDITOR_IN_CHIEF, _("Editor-in-chief")),
    (EXECUTIVE_EDITOR, _("Editor")),
    (ASSOCIATE_EDITOR, _("Associate editor")),
    (TECHNICAL_TEAM, _("Technical team")),
]
