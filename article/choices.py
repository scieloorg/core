from django.utils.translation import gettext_lazy as _

DATA_STATUS_PENDING = "PENDING"
DATA_STATUS_DELETED = "DELETED"
DATA_STATUS_MOVED = "MOVED"
DATA_STATUS_PUBLIC = "PUBLIC"
DATA_STATUS_UNDEF = "UNDEF"
DATA_STATUS_INVALID = "NVALID"
DATA_STATUS_COMPLETED = "COMPLET"
DATA_STATUS_DUPLICATED = "DUP"
DATA_STATUS_DEDUPLICATED = "DEDUP"

DATA_STATUS = (
    (DATA_STATUS_PUBLIC, _("public")),
    (DATA_STATUS_PENDING, _("pending")),
    (DATA_STATUS_MOVED, _("moved")),
    (DATA_STATUS_DELETED, _("deleted")),
    (DATA_STATUS_UNDEF, _("undefined")),
    (DATA_STATUS_INVALID, _("invalid")),
    (DATA_STATUS_COMPLETED, _("completed")),
    (DATA_STATUS_DUPLICATED, _("duplicated")),
    (DATA_STATUS_DEDUPLICATED, _("deduplicated")),
)

DATA_STATUS_EXCLUSION_LIST = [
    DATA_STATUS_DELETED,
    DATA_STATUS_MOVED,
    DATA_STATUS_INVALID,
    DATA_STATUS_DUPLICATED,
]
DATA_STATUS_INCLUSION_LIST = [
    DATA_STATUS_COMPLETED,
    DATA_STATUS_PUBLIC,
    DATA_STATUS_PENDING,
    DATA_STATUS_UNDEF,
    DATA_STATUS_DEDUPLICATED,
]

# Data availability status constants
DATA_AVAILABILITY_STATUS_AVAILABLE = "data-available"
DATA_AVAILABILITY_STATUS_UPON_REQUEST = "data-available-upon-request"
DATA_AVAILABILITY_STATUS_IN_ARTICLE = "data-in-article"
DATA_AVAILABILITY_STATUS_NOT_AVAILABLE = "data-not-available"
DATA_AVAILABILITY_STATUS_UNINFORMED = "uninformed"
DATA_AVAILABILITY_STATUS_ABSENT = "absent"
DATA_AVAILABILITY_STATUS_NOT_PROCESSED = "not-processed"

# Data availability status choices tuple
DATA_AVAILABILITY_STATUS = (
    (DATA_AVAILABILITY_STATUS_AVAILABLE, _("Os dados de pesquisa estão disponíveis em repositório.")),
    (DATA_AVAILABILITY_STATUS_UPON_REQUEST, _("Os dados de pesquisa só estão disponíveis mediante solicitação.")),
    (DATA_AVAILABILITY_STATUS_IN_ARTICLE, _("Os dados de pesquisa estão disponíveis no corpo do documento.")),
    (DATA_AVAILABILITY_STATUS_NOT_AVAILABLE, _("Os dados de pesquisa não estão disponíveis.")),
    (DATA_AVAILABILITY_STATUS_UNINFORMED, _("Uso de dados não informado; nenhum dado de pesquisa gerado ou utilizado.")),
    (DATA_AVAILABILITY_STATUS_ABSENT, _("Informação ausente no XML")),
    (DATA_AVAILABILITY_STATUS_NOT_PROCESSED, _("XML não processado")),
)