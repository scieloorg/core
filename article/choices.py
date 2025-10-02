from django.utils.translation import gettext_lazy as _

DATA_STATUS_PENDING = "PENDING"
DATA_STATUS_DELETED = "DELETED"
DATA_STATUS_MOVED = "MOVED"
DATA_STATUS_PUBLIC = "PUBLIC"
DATA_STATUS_UNDEF = "UNDEF"
DATA_STATUS_INVALID = "NVALID"

DATA_STATUS = (
    (DATA_STATUS_PUBLIC, _("public")),
    (DATA_STATUS_PENDING, _("pending")),
    (DATA_STATUS_MOVED, _("moved")),
    (DATA_STATUS_DELETED, _("deleted")),
    (DATA_STATUS_UNDEF, _("undefined")),
    (DATA_STATUS_INVALID, _("invalid")),
)

# Article types eligible for PubMed format generation
# According to https://www.ncbi.nlm.nih.gov/books/NBK3828/#publisherhelp.What_types_of_articles_are
PUBMED_ARTICLE_TYPES = [
    "research-article",
    "review-article",
    "article-commentary",
    "brief-report",
    "case-report",
    "letter",
    "rapid-communication",
    "reply",
    "editorial",
    "correction",
    "retraction",
    "addendum",
]
