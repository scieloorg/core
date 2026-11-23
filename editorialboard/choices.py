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

# Idiomas do edboard.htm no site clássico, na ordem de coleta
EDBOARD_LANGUAGES_HTML_CLASSIC_WEBSITE = [
    ("es", "Español"),
    ("pt", "Português"),
    ("en", "English"),
]

EDBOARD_FETCH_STATUS_OK = "ok"
EDBOARD_FETCH_STATUS_NOT_FOUND = "not_found"
EDBOARD_FETCH_STATUS_ERROR = "error"
EDBOARD_FETCH_STATUS = [
    (EDBOARD_FETCH_STATUS_OK, _("OK")),
    (EDBOARD_FETCH_STATUS_NOT_FOUND, _("Not found")),
    (EDBOARD_FETCH_STATUS_ERROR, _("Error")),
]
