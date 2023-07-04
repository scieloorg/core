from django.utils.translation import gettext_lazy as _

GENDER_IDENTIFICATION_STATUS = [
    ('DECLARED', _('Declarado por el investigador')), 
    ('AUTOMATIC', _('Identificado automáticamente por programa de computador')),
    ('MANUAL', _('Identificado por algun usuario'))
]

ROLE = [
    ('Editor-Chefe', _('Editor-Chefe')),
    ('Editor(es) Executivo', _('Editor(es) Executivo')),
    ('Editor(es) Associados ou de Seção', _('Editor(es) Associados ou de Seção')),
    ('Equipe Técnica', _('Equipe Técnica'))
]

MONTHS = [
    (1, _('January')),
    (2, _('February')),
    (3, _('March')),
    (4, _('April')),
    (5, _('May')),
    (6, _('June')),
    (7, _('July')),
    (8, _('August')),
    (9, _('September')),
    (10, _('October')),
    (11, _('November')),
    (12, _('December'))
]