import os
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import (
    FieldPanel,
)

from core.models import CommonControlField, Language
from core.forms import CoreAdminModelForm
from files_storage import exceptions


class MinioConfiguration(CommonControlField):

    name = models.TextField(_('Name'), null=True, blank=False)
    host = models.TextField(_('Host'), null=True, blank=True)
    bucket_root = models.TextField(_('Bucket root'), null=True, blank=True)
    bucket_app_subdir = models.TextField(
        _('Bucket app subdir'), null=True, blank=True)
    access_key = models.TextField(_('Access key'), null=True, blank=True)
    secret_key = models.TextField(_('Secret key'), null=True, blank=True)
    secure = models.BooleanField(_('Secure'), default=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['host']),
            models.Index(fields=['bucket_root']),
        ]

    panels = [
        FieldPanel('name'),
        FieldPanel('host'),
        FieldPanel('bucket_root'),
        FieldPanel('bucket_app_subdir'),
        FieldPanel('access_key'),
        FieldPanel('secret_key'),
        FieldPanel('secure'),
    ]

    base_form_class = CoreAdminModelForm

    def __str__(self):
        return f"{self.host} {self.bucket_root}"

    def __unicode__(self):
        return f"{self.host} {self.bucket_root}"

    @classmethod
    def get_or_create(
            cls,
            name, host=None,
            access_key=None, secret_key=None, secure=None,
            bucket_root=None, bucket_app_subdir=None,
            user=None,
            ):
        try:
            return cls.objects.get(name=name)
        except cls.DoesNotExist:
            files_storage = cls()
            files_storage.name = name
            files_storage.host = host
            files_storage.secure = secure
            files_storage.access_key = access_key
            files_storage.secret_key = secret_key
            files_storage.bucket_root = bucket_root
            files_storage.bucket_app_subdir = bucket_app_subdir
            files_storage.creator = user
            files_storage.save()
            return files_storage


class MinioFile(CommonControlField):
    basename = models.TextField(_('Basename'), null=True, blank=True)
    uri = models.URLField(_('URI'), null=True, blank=True)

    class Meta:

        indexes = [
            models.Index(fields=['basename']),
        ]

    def __unicode__(self):
        return f"{self.uri} {self.created}"

    def __str__(self):
        return f"{self.uri} {self.created}"

    @classmethod
    def get_or_create(cls, creator, uri, basename=None):
        try:
            return cls.objects.get(uri=uri)
        except cls.DoesNotExist:
            obj = cls()
            obj.uri = uri
            obj.basename = basename
            obj.creator = creator
            obj.save()
            return obj
        except Exception as e:
            raise exceptions.MinioFileGetOrCreateError(
                "Unable to create file: %s %s %s" %
                (type(e), e, obj)
            )
