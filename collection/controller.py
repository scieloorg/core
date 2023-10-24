import json

import requests

from core.models import Language

from .models import Collection, CollectionName


def load(user):
    response = requests.get(
        "https://articlemeta.scielo.org/api/v1/collection/identifiers/"
    )

    collections_data = json.loads(response.text)

    for collection_data in collections_data:
        collection_object = Collection.objects.filter(
            main_name=collection_data.get("original_name")
        )
        try:
            collection_object = collection_object[0]
        except IndexError:
            collection_object = Collection()
            collection_object.main_name = collection_data.get("original_name")
        collection_object.acron3 = collection_data.get("acron")
        collection_object.acron2 = collection_data.get("acron2")
        collection_object.code = collection_data.get("code")
        collection_object.domain = collection_data.get("domain")
        collection_object.save()
        names = collection_data.get("name")
        for language in names:
            collection_name = CollectionName.objects.filter(
                language=Language.get_or_create(code2=language, creator=user),
                text=names.get(language),
            )
            try:
                collection_name = collection_name[0]
            except IndexError:
                collection_name = CollectionName()
                collection_name.text = names.get(language)
                collection_name.language = Language.get_or_create(
                    code2=language, creator=user
                )
            collection_name.save()
            collection_object.name.add(collection_name)
        collection_object.status = collection_data.get("status")
        collection_object.has_analytics = collection_data.get("has_analytics")
        collection_object.collection_type = collection_data.get("type")
        collection_object.is_active = collection_data.get("is_active")
        collection_object.creator = user
        collection_object.save()
