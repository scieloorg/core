"""
Functions to build and deposit the CrossRef crossmark update policy page XML.

The crossmark update policy page is a publisher's web page that describes how
they handle corrections, retractions, and other updates to their content.
Publishers must register this page with CrossRef by depositing XML containing
the DOI and URL for the policy page.
"""
import logging
import uuid
from datetime import datetime

import requests
from lxml import etree as ET

logger = logging.getLogger(__name__)

CROSSREF_DEPOSIT_URL = "https://doi.crossref.org/servlet/deposit"
CROSSREF_TEST_DEPOSIT_URL = "https://test.crossref.org/servlet/deposit"


def _get_timestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _get_doi_batch_id():
    return uuid.uuid4().hex


def build_crossmark_policy_page_xml(
    doi,
    url,
    depositor_name,
    depositor_email_address,
    registrant,
):
    """
    Builds the CrossRef XML payload for registering the crossmark update policy
    page.

    The resulting XML follows CrossRef schema 4.4.0 and uses the
    ``<database>/<dataset>`` structure to register the policy page URL under
    the given DOI.

    Parameters
    ----------
    doi : str
        The DOI assigned to the crossmark update policy page
        (e.g. ``"10.1234/update-policy"``).
    url : str
        The URL of the crossmark update policy page
        (e.g. ``"https://journal.example.org/correction-policy"``).
    depositor_name : str
        The name of the organisation making the deposit.
    depositor_email_address : str
        The e-mail address of the depositor.
    registrant : str
        The name of the CrossRef member registrant.

    Returns
    -------
    str
        The XML content as a UTF-8 string.

    Examples
    --------
    >>> xml = build_crossmark_policy_page_xml(
    ...     doi="10.1234/update-policy",
    ...     url="https://example.org/update-policy",
    ...     depositor_name="Depositor",
    ...     depositor_email_address="depositor@example.org",
    ...     registrant="Registrant",
    ... )
    """
    nsmap = {
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }

    doi_batch = ET.Element("doi_batch", nsmap=nsmap)
    doi_batch.set("version", "4.4.0")
    doi_batch.set("xmlns", "http://www.crossref.org/schema/4.4.0")
    doi_batch.set(
        "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
        "http://www.crossref.org/schema/4.4.0 "
        "http://www.crossref.org/schemas/crossref4.4.0.xsd",
    )

    # ------------------------------------------------------------------ head
    head = ET.SubElement(doi_batch, "head")

    doi_batch_id_el = ET.SubElement(head, "doi_batch_id")
    doi_batch_id_el.text = _get_doi_batch_id()

    timestamp_el = ET.SubElement(head, "timestamp")
    timestamp_el.text = _get_timestamp()

    depositor_el = ET.SubElement(head, "depositor")
    depositor_name_el = ET.SubElement(depositor_el, "depositor_name")
    depositor_name_el.text = depositor_name
    email_address_el = ET.SubElement(depositor_el, "email_address")
    email_address_el.text = depositor_email_address

    registrant_el = ET.SubElement(head, "registrant")
    registrant_el.text = registrant

    # ------------------------------------------------------------------ body
    body = ET.SubElement(doi_batch, "body")
    database = ET.SubElement(body, "database")

    # -- database_metadata
    database_metadata = ET.SubElement(database, "database_metadata")
    database_metadata.set("language", "en")

    titles = ET.SubElement(database_metadata, "titles")
    title = ET.SubElement(titles, "title")
    title.text = "Update Policy"

    publisher = ET.SubElement(database_metadata, "publisher")
    publisher_name_el = ET.SubElement(publisher, "publisher_name")
    publisher_name_el.text = registrant

    description = ET.SubElement(database_metadata, "description")
    description.text = "Crossmark update policy page"

    # -- dataset
    dataset = ET.SubElement(database, "dataset")
    dataset.set("dataset_type", "record")

    contributors = ET.SubElement(dataset, "contributors")
    organization = ET.SubElement(contributors, "organization")
    organization.set("contributor_role", "author")
    organization.set("sequence", "first")
    organization.text = registrant

    dataset_titles = ET.SubElement(dataset, "titles")
    dataset_title = ET.SubElement(dataset_titles, "title")
    dataset_title.text = "Update Policy"

    doi_data = ET.SubElement(dataset, "doi_data")
    doi_el = ET.SubElement(doi_data, "doi")
    doi_el.text = doi
    resource_el = ET.SubElement(doi_data, "resource")
    resource_el.text = url

    xml_tree = ET.ElementTree(doi_batch)
    return ET.tostring(
        xml_tree,
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8",
    ).decode("utf-8")


def deposit_crossmark_policy_page(
    doi,
    url,
    login_id,
    login_passwd,
    depositor_name,
    depositor_email_address,
    registrant,
    is_test=False,
):
    """
    Deposits the crossmark update policy page with the CrossRef API.

    Builds the CrossRef XML payload for the given policy page DOI and URL and
    submits it to the CrossRef deposit endpoint via an HTTP POST request.

    Parameters
    ----------
    doi : str
        The DOI assigned to the crossmark update policy page
        (e.g. ``"10.1234/update-policy"``).
    url : str
        The URL of the crossmark update policy page
        (e.g. ``"https://journal.example.org/correction-policy"``).
    login_id : str
        The CrossRef member login ID (username).
    login_passwd : str
        The CrossRef member login password.
    depositor_name : str
        The name of the organisation making the deposit.  When empty or
        ``None``, ``registrant`` is used as a fallback.
    depositor_email_address : str
        The e-mail address of the depositor.
    registrant : str
        The name of the CrossRef member registrant.
    is_test : bool, optional
        When ``True`` the deposit is sent to the CrossRef test server instead
        of the production server.  Default is ``False``.

    Returns
    -------
    requests.Response
        The HTTP response returned by the CrossRef deposit API.

    Raises
    ------
    ValueError
        If any of ``doi``, ``url``, ``login_id``, or ``login_passwd`` is
        empty or ``None``.
    requests.HTTPError
        If the CrossRef API returns a non-2xx HTTP status code.

    Examples
    --------
    >>> response = deposit_crossmark_policy_page(
    ...     doi="10.1234/update-policy",
    ...     url="https://example.org/update-policy",
    ...     login_id="mylogin",
    ...     login_passwd="mypassword",
    ...     depositor_name="Depositor",
    ...     depositor_email_address="depositor@example.org",
    ...     registrant="Registrant",
    ...     is_test=True,
    ... )
    """
    if not doi:
        raise ValueError("doi is required")
    if not url:
        raise ValueError("url is required")
    if not login_id:
        raise ValueError("login_id is required")
    if not login_passwd:
        raise ValueError("login_passwd is required")

    xml_content = build_crossmark_policy_page_xml(
        doi=doi,
        url=url,
        depositor_name=depositor_name or registrant,
        depositor_email_address=depositor_email_address,
        registrant=registrant,
    )

    deposit_url = CROSSREF_TEST_DEPOSIT_URL if is_test else CROSSREF_DEPOSIT_URL
    xml_bytes = xml_content.encode("utf-8")
    filename = "crossmark_policy_{}.xml".format(doi.replace("/", "_"))

    logger.info(
        "Depositing crossmark policy page DOI %s to %s", doi, deposit_url
    )

    response = requests.post(
        deposit_url,
        data={
            "operation": "doMDUpload",
            "login_id": login_id,
            "login_passwd": login_passwd,
        },
        files={"fname": (filename, xml_bytes, "text/xml")},
        timeout=60,
    )
    response.raise_for_status()
    return response
