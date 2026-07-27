from django.utils.translation import gettext_lazy as _

ENDPOINTS = (("fix-pid-v2", "fix-pid-v2"),)

# article is not public
PPXML_STATUS_WAIT = "WAIT"
# 
PPXML_STATUS_IGNORED = "IGNORE"
# ready to create article
PPXML_STATUS_TODO = "TODO"
# article was created
PPXML_STATUS_DONE = "DONE"
PPXML_STATUS_UNDEF = "UNDEF"
# xml is broken
PPXML_STATUS_INVALID = "NVALID"
# journal / issue in xml is not registered
PPXML_STATUS_UNMATCHED_JOURNAL_OR_ISSUE = "UNMATCH"
# is duplicated
PPXML_STATUS_DUPLICATED = "DUP"
# removed the duplication
PPXML_STATUS_DEDUPLICATED = "DEDUP"

PPXML_STATUS = (
    (PPXML_STATUS_TODO, _("To do")),
    (PPXML_STATUS_DONE, _("Done")),
    (PPXML_STATUS_WAIT, _("waiting")),
    (PPXML_STATUS_IGNORED, _("ignore")),
    (PPXML_STATUS_UNDEF, _("undefined")),
    (PPXML_STATUS_INVALID, _("invalid")),
    (PPXML_STATUS_DUPLICATED, _("duplicated")),
    (PPXML_STATUS_DEDUPLICATED, _("deduplicated")),
    (PPXML_STATUS_UNMATCHED_JOURNAL_OR_ISSUE, _("unmatched journal or issue")),
)

PPXML_STATUS_TO_CREATE_OR_UPDATE_ARTICLE_SOURCE = [
    PPXML_STATUS_INVALID,
    PPXML_STATUS_WAIT,
]
PPXML_STATUS_TO_IGNORE = [
    PPXML_STATUS_INVALID,
    PPXML_STATUS_DONE,
    PPXML_STATUS_WAIT,
    PPXML_STATUS_IGNORED,
    PPXML_STATUS_UNDEF,
    PPXML_STATUS_DUPLICATED,
    PPXML_STATUS_DEDUPLICATED,
    PPXML_STATUS_UNMATCHED_JOURNAL_OR_ISSUE,
]