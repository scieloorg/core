from core.utils.utils import fetch_data
from dataset.models import (
    Affiliation,
    Author,
    Dataset,
    Dataverse,
    File,
    InstitutionDataSet,
    Publication,
    Publisher,
)
from thematic_areas.models import ThematicArea
from vocabulary.models import Keyword

from dataset.utils.fields_data import fields_dataset, fields_file, fields_dataverse


def load_from_data_scielo(user):
    rows = 10
    start = 0
    condition = True
    dict_func = {
        "dataverse": process_dataverses,
        "dataset": process_datasets,
        "file": process_files,
    }

    while condition:
        url = "https://data.scielo.org/api/search?q=*" + "&start=" + str(start)
        data = fetch_data(url, json=True, timeout=30, verify=True)
        total = data["data"]["total_count"]
        for data in data["data"]["items"]:
            func = dict_func.get(data["type"])
            if func:
                fields_name = "fields_" + data["type"]
                fields = globals().get(fields_name)
                relevant_data = {k: data[k] for k in fields if k in data}
                func(user, **relevant_data)

        start += rows
        condition = start < total


def process_dataverses(user, **kwargs):
    obj = Dataverse.create_or_update(**kwargs, user=user)
    return obj


def process_datasets(user, **kwargs):
    obj = Dataverse.create_or_update(
        identifier=kwargs.get("identifier_of_dataverse"), user=user
    )
    authors = get_or_create_authors(authors=kwargs.get("authors"), user=user)
    keywords = get_or_create_keywords(keywords=kwargs.get("keywords"), user=user)
    thematic_area = get_or_create_thematic_area(
        thematic_area=kwargs.get("subjects"), user=user
    )
    contacts = get_or_create_contacts(contacts=kwargs.get("contacts"), user=user)
    publisher = get_or_create_publisher(publisher=kwargs.get("publisher"), user=user)
    publication = get_or_create_publications(
        publications=kwargs.get("publications"), user=user
    )
    kwargs.update(
        {
            "identifier_of_dataverse": obj,
            "authors": authors,
            "keywords": keywords,
            "thematic_area": thematic_area,
            "contacts": contacts,
            "publisher": publisher,
            "publications": publication,
        }
    )
    obj = Dataset.create_or_update(**kwargs, user=user)


def process_files(user, **kwargs):
    dataset = Dataset.create_or_update(
        global_id=kwargs.get("dataset_persistent_id"),
        user=user,
    )
    kwargs.update({"dataset_persistent_id": dataset})
    obj = File.create_or_update(**kwargs, user=user)


def get_or_create_authors(authors, user):
    data = []
    if authors:
        for author in authors:
            obj, created = Author.objects.get_or_create(
                name=author,
                creator=user,
            )
            data.append(obj)
    return data


def get_or_create_keywords(keywords, user):
    data = []
    if keywords:
        for keyword in keywords:
            obj = Keyword.get_or_create(text=keyword, language=None, user=user)
            data.append(obj)
    return data


def get_or_create_thematic_area(thematic_area, user):
    data = []
    if thematic_area:
        for ta in thematic_area:
            obj = ThematicArea.get_or_create(
                level0=None, level1=ta, level2=None, user=user
            )
            data.append(obj)
    return data


def get_or_create_contacts(contacts, user):
    data = []
    if contacts:
        for ct in contacts:
            researcher = get_or_create_authors(authors=[ct.get("name")], user=user)
            inst, _ = InstitutionDataSet.objects.get_or_create(
                name=ct.get("affiliation")
            )
            obj, _ = Affiliation.objects.get_or_create(
                institution=inst,
                author=researcher[0],
                creator=user,
            )
            data.append(obj)
    return data


def get_or_create_publisher(publisher, user):
    obj, _ = Publisher.objects.get_or_create(
        name=publisher,
        creator=user,
    )
    return obj


def get_or_create_publications(publications, user):
    """
    Ex publications:

    [{'citation': 'Prevalência, fatores de risco associados, e doenças crônicas em idosos longevos'}, {}, {}]

    """
    data = []
    if publications:
        for publication in publications:
            if publication:
                obj, _ = Publication.objects.get_or_create(
                    citation=publication.get("citation"),
                    url=publication.get("url"),
                    creator=user,
                )
                data.append(obj)
    return data
