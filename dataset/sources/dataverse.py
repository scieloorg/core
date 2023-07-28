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
                func(user, data)

        start += rows
        condition = start < total


def process_dataverses(user, kwargs):
    obj = Dataverse.create_or_update(
        name=kwargs.get("name"),
        identifier=kwargs.get("identifier"),
        type=kwargs.get("type"),
        url=kwargs.get("url"),
        published_at=kwargs.get("published_at"),
        description=kwargs.get("description"),
        user=user,
    )


def process_datasets(user, kwargs):
    obj, created = Dataverse.objects.get_or_create(
        identifier=kwargs.get("identifier_of_dataverse"),
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
    obj = Dataset.create_or_update(
        global_id=kwargs.get("global_id"),
        name=kwargs.get("name"),
        type=kwargs.get("type"),
        url=kwargs.get("url"),
        published_at=kwargs.get("published_at"),
        description=kwargs.get("description"),
        citation_html=kwargs.get("citationHtml"),
        citation=kwargs.get("citation"),
        publisher=publisher,
        dataverse=obj,
        authors=authors,
        keywords=keywords,
        thematic_area=thematic_area,
        contacts=contacts,
        publications=publication,
    )


def process_files(user, kwargs):
    dataset, created = Dataset.objects.get_or_create(
        global_id=kwargs.get("dataset_persistent_id"),
    )
    obj = File.create_or_update(
        file_persistent_id=kwargs.get("file_persistent_id"),
        name=kwargs.get("name"),
        type=kwargs.get("type"),
        url=kwargs.get("url"),
        published_at=kwargs.get("published_at"),
        file_type=kwargs.get("file_type"),
        file_content_type=kwargs.get("file_content_type"),
        dataset=dataset,
        user=user,
    )


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
