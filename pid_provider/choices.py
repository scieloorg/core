from django.utils.translation import gettext_lazy as _

ENDPOINTS = (("fix-pid-v2", "fix-pid-v2"),)

PPXML_STATUS_WAIT = "WAIT"
PPXML_STATUS_IGNORED = "IGNORE"
PPXML_STATUS_TODO = "TODO"
PPXML_STATUS_DONE = "DONE"
PPXML_STATUS_UNDEF = "UNDEF"

PPXML_STATUS = (
    (PPXML_STATUS_TODO, _("To do")),
    (PPXML_STATUS_DONE, _("Done")),
    (PPXML_STATUS_WAIT, _("waiting")),
    (PPXML_STATUS_IGNORED, _("ignore")),
    (PPXML_STATUS_UNDEF, _("undefined")),
)
