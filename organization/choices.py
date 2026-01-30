from django.utils.translation import gettext_lazy as _


SOURCE_CHOICES = [
    ("user", _("user")),
    ("legacy", _("legacy")),
    ("MEC", _("Ministério da Educação e Cultura")),
    ("ror", _("Research Organization Registry")),
]

DATA_STATUS_CHOICES = [
    ("raw", _("raw")),
    ("pending", _("pending")),
    ("certified", _("certified")), # validada por um agente confiável
    ("invalid", _("invalid")),
    ("matched", _("matched")), # relacionada com um registro certified
]