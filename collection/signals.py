from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Collection
from .tasks import build_collection_webhook


@receiver(post_save, sender=Collection, dispatch_uid="collection.signals.post_save")
def collection_post_save(sender, instance, created, **kwargs):
    def _on_commit():
        event = "collection.created" if created else "collection.updated"
        build_collection_webhook.apply_async(
            kwargs=dict(
                event=event,
                collection_acron=instance.acron3,
                # headers=headers,
            )
        )
    transaction.on_commit(_on_commit)