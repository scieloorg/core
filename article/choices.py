from django.utils.translation import gettext as _


DATA_STATUS_PENDING = "PENDING"
DATA_STATUS_DELETED = "DELETED"
DATA_STATUS_MOVED = "MOVED"
DATA_STATUS_PUBLIC = "PUBLIC"
DATA_STATUS_UNDEF = "UNDEF"

DATA_STATUS = (
    (DATA_STATUS_PUBLIC, _("public")),
    (DATA_STATUS_PENDING, _("pending")),
    (DATA_STATUS_MOVED, _("moved")),
    (DATA_STATUS_DELETED, _("deleted")),
    (DATA_STATUS_UNDEF, _("undefined")),
)
