from django.utils.translation import gettext_lazy as _

SOCIAL_NETWORK_NAMES = [
    ("facebook", "Facebook"),
    ("twitter", "Twitter"),
]

OA_STATUS = [
    ("", ""),
    ("diamond", "Diamond"),
    ("gold", "Gold"),
    ("hybrid", "Hybrid"),
    ("bronze", "Bronze"),
    ("green", "Green"),
    ("closed", "Closed"),
]

STATUS = [
    ("?", _("Unknow")),
    ("C", _("Current")),
    ("D", _("Ceased")),
    ("R", _("Reports only")),
    ("S", _("Suspended")),
]

PUBLISHING_MODEL = [
    ("continuous", _("Continuous")),
    ("undefined", _("Undefined")),
]

FREQUENCY = [
    ("?", _("Unknown")),
    ("A", _("Annual")),
    ("B", _("Bimonthly (every two months)")),
    ("C", _("Semiweekly (twice a week)")),
    ("D", _("Daily")),
    ("E", _("Biweekly (every two weeks)")),
    ("F", _("Semiannual (twice a year)")),
    ("G", _("Biennial (every two years)")),
    ("H", _("Triennial (every three years)")),
    ("I", _("Three times a week")),
    ("J", _("Three times a month")),
    ("K", _("Irregular (known to be so)")),
    ("M", _("Monthly")),
    ("Q", _("Quarterly")),
    ("S", _("Semimonthly (twice a month)")),
    ("T", _("Three times a year")),
    ("W", _("Weekly")),
    ("Z", _("Other frequencies")),
]

ALPHABET_OF_TITLE = [
    ("A", _("Basic Roman")),
    ("B", _("Extensive Roman")),
    ("C", _("Cirillic")),
    ("D", _("Japanese")),
    ("E", _("Chinese")),
    ("K", _("Korean")),
    ("O", _("Another alphabet")),
]

STANDARD = [
    ("apa", _("American Psychological Association")),
    ("iso690", _("iso 690/87 - international standard organization")),
    ("nbr6023", _("nbr 6023/89 - Associação Brasileira de Normas Técnicas")),
    ("other", _("other standard")),
    (
        "vancouv",
        _(
            "the vancouver group - uniform requirements for manuscripts submitted to biomedical journals"
        ),
    ),
]

LITERATURE_TYPE = [
    ("C", _("Conference")),
    ("M", _("Monograph")),
    ("MC", _("Conference papers as Monograph")),
    ("MP", _("Project papers as Monograph")),
    ("MPC", _("Project and Conference papers as monograph")),
    ("MS", _("Monograph Series")),
    ("MSC", _("Conference papers as Monograph Series")),
    ("MSP", _("Project papers as Monograph Series")),
    ("N", _("Document in a non conventional form")),
    ("NC", _("Conference papers in a non conventional form")),
    ("NP", _("Project papers in a non conventional form")),
    ("P", _("Project")),
    ("S", _("Serial")),
    ("SC", _("Conference papers as Periodical Series")),
    ("SCP", _("Conference and Project papers as periodical series")),
    ("SP", _("Project papers as Periodical Series")),
    ("T", _("Thesis and Dissertation")),
    ("TS", _("Thesis Series")),
]

PUBLICATION_LEVEL = [
    ("CT", _("Scientific/technical")),
    ("DI", _("Divulgation")),
]


TREATMENT_LEVEL = [
    ("am", _("Analytical of a monograph")),
    ("amc", _("Analytical of a monograph in a collection")),
    ("ams", _("Analytical of a monograph in a serial")),
    ("as", _("Analytical of a serial")),
    ("c", _("Collective level")),
    ("m", _("Monographic level")),
    ("mc", _("Monographic in a collection")),
    ("ms", _("Monographic series level")),
]

TYPE = [
    ("DATABASE", _("DATABASE")),
    ("DIRECTORY", _("DIRECTORY")),
    ("OTHER", _("OTHER")),
]

STUDY_AREA = [
    ("Agricultural Sciences", _("Agricultural Sciences")),
    ("Applied Social Sciences", _("Applied Social Sciences")),
    ("Biological Sciences", _("Biological Sciences")),
    ("Engineering", _("Engineering")),
    ("Exact and Earth Sciences", _("Exact and Earth Sciences")),
    ("Health Sciences", _("Health Sciences")),
    ("Human Sciences", _("Human Sciences")),
    ("Linguistics, Letters and Arts", _("Linguistic, Literature and Arts")),
    ("Psicanalise", _("Psicanalise")),
]

WOS_DB = [
    ("SCIE", _("Science Citation Index Expanded")),
    ("SSCI", _("Social Sciences Citation Index")),
    ("A&HCI", _("Arts Humanities Citation Index")),
]


# Apr 1998: Admitted to the collection.
# Aug 2008: Indexing interrupted (Reason: suspended-by-committee).
# Sep 2009: Admitted to the collection.
# Jun 2012: Indexing interrupted (Reason: suspended-by-committee).
JOURNAL_EVENT_TYPE = [
    ("ADMITTED", _("Admitted to the collection")),
    ("INTERRUPTED", _("Indexing interrupted")),
]

# D | Ceased
# S |not-open-access  Not open access
# S |suspended-by-committee   Indexing interrupted by committee
# S |suspended-by-editor  Indexing interrupted by editor

INDEXING_INTERRUPTION_REASON = [
    ("ceased", _("Ceased journal")),
    ("not-open-access", _("Not open access")),
    ("by-committee", _("by the committee")),
    ("by-editor", _("by the editor")),
]

COINS = [
    ("USD", "US Dollar"),
    ("EUR", "Euro"),
    ("JPY", "Japanese Yen"),
    ("GBP", "British Pound Sterling"),
    ("AUD", "Australian Dollar"),
    ("CAD", "Canadian Dollar"),
    ("CHF", "Swiss Franc"),
    ("CNY", "Chinese Yuan"),
    ("SEK", "Swedish Krona"),
    ("NZD", "New Zealand Dollar"),
    ("BRL", "Brazilian Real"),
]
