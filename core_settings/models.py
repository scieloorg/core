from django.db import models
from django.utils.translation import gettext as _

from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel, TabbedInterface, ObjectList
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.contrib.settings.models import BaseSetting, register_setting


@register_setting
class CustomSettings(BaseSetting):
    """
    This a settings model.

    More about look:
        https://docs.wagtail.org/en/stable/reference/contrib/settings.html
    """
    class Meta:
        verbose_name = _('Configuração do site')
        verbose_name_plural = _('Configuração do site')

    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)

    footer_text = RichTextField(null=True, blank=True)

    favicon = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    admin_logo = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    site_logo = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    site_panels = [
        FieldPanel('name'),
        FieldPanel('email'),
        FieldPanel('phone'),
        FieldPanel('footer_text', classname="full"),
        ImageChooserPanel('favicon'),
        ImageChooserPanel('site_logo'),
    ]

    admin_panels = [
        ImageChooserPanel('admin_logo'),
    ]

    edit_handler = TabbedInterface([
        ObjectList(site_panels, heading=_('Site settings')),
        ObjectList(admin_panels, heading=_('Admin settings')),
    ])

