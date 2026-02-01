from django.utils.translation import gettext_lazy as _


SOURCE_CHOICES = [
    ("user", _("user")),
    ("legacy", _("legacy")),
    ("MEC", _("Ministério da Educação e Cultura")),
    ("ror", _("Research Organization Registry")),
]


ORGANIZATION_ROLES = [
    ("coordinator", _("Coordinator")),
    ("owner", _("Owner")),
    ("publisher", _("Publisher")),
    ("sponsor", _("Sponsor")),
    ("copyright_holder", _("Copyright Holder")),
    ("partner", _("Partner")),
    ("funder", _("Funder")),
    ("host", _("Host")),
    ("provider", _("Provider")),
    ("company", _("Company")),
]
