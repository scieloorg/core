import logging
import re
from datetime import datetime
from urllib.parse import urlparse

from lxml import etree
from sickle import Sickle

from article import models
from article.utils.parse_name_author import parse_author_name
from institution.models import Publisher

namespaces = {
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class PreprintArticleSaveError(Exception): ...


def harvest_preprints(URL, user):
    sickle = Sickle(URL)
    recs = sickle.ListRecords(metadataPrefix="oai_dc")
    for rec in recs:
        article_info = get_info_article(rec)
        identifier = get_doi(article_info["identifier"])
        doi = get_or_create_doi(doi=identifier, user=user)

        article = models.Article.objects.create(
            doi=doi,
            creator=user,
        )
        try:
            set_dates(article=article, date=article_info.get("date"))
            article.titles.set(
                get_or_create_titles(titles=article_info.get("title"), user=user)
            )

            try:
                year = article.issue.year
            except AttributeError:
                year = None
            article.researchers.set(
                get_or_create_researches(
                    user, authors=article_info.get("authors"), year=year
                )
            )
            article.keywords.set(
                get_or_create_keyword(keywords=article_info.get("subject"), user=user)
            )
            article.license_statements.set(
                get_or_create_license(rights=article_info.get("rights"), user=user)
            )
            article.abstracts.set(
                get_or_create_abstracts(
                    article=article,
                    description=article_info.get("description"),
                    user=user,
                )
            )
            article.languages.add(
                get_or_create_language(lang=article_info.get("language"), user=user)
            )
            article.publisher = get_publisher(
                user, publisher=article_info.get("publisher")
            )
            for ls in article.license_statements.iterator():
                article.license = ls.license
                break
            article.save()
        except Exception as e:
            # TODO cria um registro das falhas de modo que fiquem
            # acessíveis na área administrativa
            # para que o usuário fique sabendo quais itens falharam
            raise PreprintArticleSaveError(e)


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
            name_author = author.text.strip()
            author_dict = parse_author_name(name_author)
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
        obj = models.Keyword.create_or_update(
            user=user,
            vocabulary=None,
            language=get_or_create_language(kwd.get("lang"), user=user),
            text=kwd.get("text"),
        )
        data.append(obj)
    return data


def get_or_create_license(rights, user):
    """
    EX:'rights': [{'text': 'Copyright (c) 2020 Julio Croda, Wanderson Kleber de  Oliveira, Rodrigo Lins  Frutuoso, Luiz Henrique  Mandetta, Djane Clarys  Baia-da-Silva, José Diego  Brito-Sousa, Wuelton Marcelo  Monteiro, Marcus Vinícius Guimarães  Lacerda', 'lang': 'en-US'}, {'text': 'https://creativecommons.org/licenses/by/4.0', 'lang': 'en-US'}],
    """
    data = []

    url = None
    license = None
    license_p = None
    license_type = None
    language = None

    for item in rights:
        # item = {"text": url or license_p, "lang": ""}
        language = language or item.get("lang")
        content = item.get("text")
        parsed_url = urlparse(content)

        if parsed_url.scheme in [
            "http",
            "https",
        ]:
            url = content
        else:
            license_p = content

    if url:
        url_data = models.LicenseStatement.parse_url(url)
        license_type = url_data.get("license_type")

        if license_type:
            license = models.License.create_or_update(
                user,
                license_type=license_type,
            )

        license_statement = models.LicenseStatement.create_or_update(
            user=user,
            url=url,
            license_p=license_p,
            language=get_or_create_language(language, user=user),
            license=license,
        )

        data.append(license_statement)
    return data


def get_or_create_abstracts(article, description, user):
    data = []
    for abstract in description:
        obj = models.DocumentAbstract.create_or_update(
            article=article,
            text=abstract.get("text"),
            language=get_or_create_language(abstract.get("lang"), user=user),
            user=user,
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


def get_publisher(user, publisher):
    return Publisher.get_or_create(
        user=user,
        name=publisher[0]["text"],
        acronym=None,
        level_1=None,
        level_2=None,
        level_3=None,
        location=None,
        official=None,
        is_official=None,
        url=None,
        institution_type=None,
    )


def set_dates(article, date):
    article.set_date_pub(date)


def get_or_create_researches(user, authors, year):
    data = []
    for author in authors:
        # em preprint, por enquanto existem apenas:
        # given_names, surname, declared_name
        obj = models.Researcher.create_or_update(
            user=user,
            given_names=author.get("given_names"),
            last_name=author.get("surname"),
            declared_name=author.get("declared_name"),
            email=author.get("email"),
            affiliation=author.get("affiliation"),
            suffix=author.get("suffix"),
            orcid=author.get("orcid"),
            lattes=author.get("lattes"),
            year=year,
        )
        data.append(obj)
    return data
