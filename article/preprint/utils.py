import re
import logging

from lxml import etree
from datetime import datetime
from urllib.parse import urlparse

from article import models


namespaces = {
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

def get_info_article(rec):
    article_dict = {}
    root = etree.fromstring(str(rec))

    nodes = [
        "title",
        "subject",
        "identifier",
        "rights",
        "publisher",
        "description",
        "publisher",
    ]
    for node in nodes:
        article_dict[node] = []
        for x in root.xpath(f".//dc:{node}", namespaces=namespaces):
            node_dict = {"text": x.text}
            lang = x.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang:
                node_dict["lang"] = lang
            article_dict[node].append(node_dict)

        try:
            language = root.xpath(".//dc:language", namespaces=namespaces)[0].text
            article_dict["language"] = language
        except IndexError as e:
            logging.exception(f"Not found title in {rec.header.identifier}. Error: {e}")

        try:
            date_string = root.xpath(".//dc:date", namespaces=namespaces)[0].text
            date = datetime.strptime(date_string, "%Y-%m-%d")
            article_dict["date"] = {
                "day": date.day,
                "month": date.month,
                "year": date.year,
            }
        except IndexError as e:
            logging.exception(f"Not found date in {rec.header.identifier}. Error: {e}")

        author_data = []
        for author in root.xpath(".//dc:creator", namespaces=namespaces):
            name_author = [name.strip() for name in author.text.split(",")][::1]
            author_dict = {}
            for i, name in enumerate(("given_names", "surname")[:len(name_author)]):
                try:
                    author_dict.update({f"{name}": name_author[i]})
                except IndexError as e:
                    logging.exception(
                        f"Error in authors: {e}.  Artigo: {rec.header.identifier}"
                    )
            author_data.append(author_dict)
        article_dict["authors"] = author_data
    return article_dict


def get_or_create_doi(doi, user):
    data = []
    for d in doi:
        ## TODO
        ## Relacionar com modelo language
        obj = models.DOI.get_or_create(
            value=d.get("text"),
            language=get_or_create_language(d.get("lang"), user=user),
            creator=user,
        )
        data.append(obj)
    return data


def get_or_create_titles(titles, user):
    data = []
    for title in titles:
        ## TODO
        # ## Criar get_or_create para DocumentTitle
        obj, created = models.DocumentTitle.objects.get_or_create(
            plain_text=title.get("text"),
            language=get_or_create_language(title.get("lang"), user=user),
            creator=user,
        )
        data.append(obj)
    return data


def get_or_create_keyword(keywords, user):
    data = []
    for kwd in keywords:
        obj = models.Keyword.get_or_create(
            text=kwd.get("text"),
            language=get_or_create_language(kwd.get("lang"), user=user),
            user=user,
        )
        data.append(obj)
    return data


def get_or_create_license(rights, user):
    """
    EX:'rights': [{'text': 'Copyright (c) 2020 Julio Croda, Wanderson Kleber de  Oliveira, Rodrigo Lins  Frutuoso, Luiz Henrique  Mandetta, Djane Clarys  Baia-da-Silva, José Diego  Brito-Sousa, Wuelton Marcelo  Monteiro, Marcus Vinícius Guimarães  Lacerda', 'lang': 'en-US'}, {'text': 'https://creativecommons.org/licenses/by/4.0', 'lang': 'en-US'}],
    """
    data = []
    for license in rights:
        parsed_url = urlparse(license.get("text"))
        if parsed_url.scheme in [
            "http",
            "https",
        ]:
            url = license.get("text")
            license_p = None
        else:
            url = None
            license_p = license.get("text")

        obj = models.License.get_or_create(
            url=url,
            license_p=license_p,
            language=get_or_create_language(license.get("lang"), user=user),
            license_type=None,
            creator=user,
        )
        data.append(obj)
    return data


def get_or_create_abstracts(description, user):
    data = []
    for abstract in description:
        obj, created = models.DocumentAbstract.objects.get_or_create(
            plain_text=abstract.get("text"),
            language=get_or_create_language(abstract.get("lang"), user=user),
            creator=user,
        )
        data.append(obj)
    return data


def get_or_create_language(lang, user):
    obj = models.Language.get_or_create(code2=lang, creator=user)
    return obj


def get_doi(identifier):
    pattern = r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$"
    data = []
    for doi in identifier:
        if re.findall(pattern, doi["text"], re.IGNORECASE):
            data.append(doi)
    return data


def get_publisher(publisher):
    try:
        return models.Institution.objects.get(name=publisher[0]["text"])
    except (models.Institution.DoesNotExist, IndexError):
        return None


def set_dates(article, date):
    article.set_date_pub(date)


def get_or_create_researches(authors):
    data = []
    for author in authors:
        obj = models.Researcher.get_or_create(
            given_names=author.get('given_names'),
            last_name=author.get('surname'),
            suffix=None,
            orcid=None,
            lattes=None        
        )
        data.append(obj)
    return data