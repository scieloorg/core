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
DATA_AVAILABILITY_STATUS_INVALID = "invalid"

# Data availability status choices tuple
DATA_AVAILABILITY_STATUS = (
    (DATA_AVAILABILITY_STATUS_AVAILABLE, _("Os dados de pesquisa estão disponíveis em repositório.")),
    (DATA_AVAILABILITY_STATUS_UPON_REQUEST, _("Os dados de pesquisa só estão disponíveis mediante solicitação.")),
    (DATA_AVAILABILITY_STATUS_IN_ARTICLE, _("Os dados de pesquisa estão disponíveis no corpo do documento.")),
    (DATA_AVAILABILITY_STATUS_NOT_AVAILABLE, _("Os dados de pesquisa não estão disponíveis.")),
    (DATA_AVAILABILITY_STATUS_UNINFORMED, _("Uso de dados não informado; nenhum dado de pesquisa gerado ou utilizado.")),
    (DATA_AVAILABILITY_STATUS_ABSENT, _("Informação ausente no XML")),
    (DATA_AVAILABILITY_STATUS_NOT_PROCESSED, _("XML não processado")),
    (DATA_AVAILABILITY_STATUS_INVALID, _("Valor inválido recebido do XML")),
)

# Lista com valores válidos para validação
DATA_AVAILABILITY_STATUS_VALID_VALUES = [
    DATA_AVAILABILITY_STATUS_AVAILABLE,
    DATA_AVAILABILITY_STATUS_UPON_REQUEST,
    DATA_AVAILABILITY_STATUS_IN_ARTICLE,
    DATA_AVAILABILITY_STATUS_NOT_AVAILABLE,
    DATA_AVAILABILITY_STATUS_UNINFORMED,
]

# Constantes para cada tipo de relacionamento
RELATED_TYPE_CORRECTED_ARTICLE = 'corrected-article'
RELATED_TYPE_CORRECTION_FORWARD = 'correction-forward'
RELATED_TYPE_RETRACTED_ARTICLE = 'retracted-article'
RELATED_TYPE_RETRACTION_FORWARD = 'retraction-forward'
RELATED_TYPE_PARTIAL_RETRACTION = 'partial-retraction'
RELATED_TYPE_PARTIAL_RETRACTION_FORWARD = 'partial-retraction-forward'
RELATED_TYPE_ADDENDED_ARTICLE = 'addended-article'
RELATED_TYPE_ADDENDUM = 'addendum'
RELATED_TYPE_EXPRESSION_OF_CONCERN = 'expression-of-concern'
RELATED_TYPE_OBJECT_OF_CONCERN = 'object-of-concern'
RELATED_TYPE_COMMENTARY_ARTICLE = 'commentary-article'
RELATED_TYPE_COMMENTARY = 'commentary'
RELATED_TYPE_REPLY_TO_COMMENTARY = 'reply-to-commentary'
RELATED_TYPE_COMMENTARY_REPLY_OBJECT = 'commentary-reply-object'
RELATED_TYPE_LETTER = 'letter'
RELATED_TYPE_LETTER_OBJECT = 'letter-object'
RELATED_TYPE_REPLY_TO_LETTER = 'reply-to-letter'
RELATED_TYPE_LETTER_REPLY_OBJECT = 'letter-reply-object'
RELATED_TYPE_REVIEWED_ARTICLE = 'reviewed-article'
RELATED_TYPE_REVIEWER_REPORT = 'reviewer-report'
RELATED_TYPE_PREPRINT = 'preprint'
RELATED_TYPE_PUBLISHED_ARTICLE = 'published-article'

# Choices para tipos de relacionamentos entre artigos
RELATED_ARTICLE_TYPE_CHOICES = [
    # Erratas e correções
    (RELATED_TYPE_CORRECTED_ARTICLE, _('Errata')),
    (RELATED_TYPE_CORRECTION_FORWARD, _('Documento corrigido pela errata')),

    # Retrações
    (RELATED_TYPE_RETRACTED_ARTICLE, _('Retratação total')),
    (RELATED_TYPE_RETRACTION_FORWARD, _('Documento retratado totalmente')),
    (RELATED_TYPE_PARTIAL_RETRACTION, _('Retratação parcial')),
    (RELATED_TYPE_PARTIAL_RETRACTION_FORWARD, _('Documento retratado parcialmente')),

    # Adendos
    (RELATED_TYPE_ADDENDED_ARTICLE, _('Adendo')),
    (RELATED_TYPE_ADDENDUM, _('Documento objeto do adendo')),

    # Manifestações de preocupação
    (RELATED_TYPE_EXPRESSION_OF_CONCERN, _('Manifestação de preocupação')),
    (RELATED_TYPE_OBJECT_OF_CONCERN, _('Documento objeto de manifestação de preocupação')),

    # Comentários e respostas
    (RELATED_TYPE_COMMENTARY_ARTICLE, _('Comentário')),
    (RELATED_TYPE_COMMENTARY, _('Documento comentado')),
    (RELATED_TYPE_REPLY_TO_COMMENTARY, _('Resposta para um comentário')),
    (RELATED_TYPE_COMMENTARY_REPLY_OBJECT, _('Comentário objeto da resposta')),

    # Cartas e respostas
    (RELATED_TYPE_LETTER, _('Carta')),
    (RELATED_TYPE_LETTER_OBJECT, _('Documento a que se refere a carta')),
    (RELATED_TYPE_REPLY_TO_LETTER, _('Resposta para uma carta')),
    (RELATED_TYPE_LETTER_REPLY_OBJECT, _('Carta objeto da resposta')),

    # Pareceres
    (RELATED_TYPE_REVIEWED_ARTICLE, _('Parecer (revisão por pares)')),
    (RELATED_TYPE_REVIEWER_REPORT, _('Documento com parecer (revisão por pares)')),

    # Preprints
    (RELATED_TYPE_PREPRINT, _('Manuscrito disponibilizado em acesso aberto em servidor de preprints')),
    (RELATED_TYPE_PUBLISHED_ARTICLE, _('Artigo publicado baseado no preprint')),
]
