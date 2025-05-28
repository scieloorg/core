from django.db.models import Q
from django.utils.translation import gettext as _

from pid_provider import exceptions


def get_valid_query_parameters(xml_adapter):
    q = (get_journal_q_expression(xml_adapter)) & (get_pub_year_expression(xml_adapter))

    basic_params = get_basic_params(xml_adapter)
    if xml_adapter.is_aop:
        kwargs = [_get_valid_params(xml_adapter, basic_params)]
    else:
        kwargs = [
            _get_valid_params(
                xml_adapter,
                basic_params,
                get_issue_params(xml_adapter, filter_by_issue=True),
            ),
            _get_valid_params(
                xml_adapter,
                basic_params,
                get_issue_params(xml_adapter, aop_version=True),
            ),
        ]
    return q, kwargs


def _get_valid_params(xml_adapter, basic_params, issue_params=None):
    valid_params = {}
    valid_params.update(basic_params)
    if issue_params:
        valid_params.update(issue_params)
    try:
        validate_query_params(valid_params)
    except exceptions.RequiredAuthorErrorToGetPidProviderXMLError:
        try:
            disambiguation_params = get_disambiguation_params(xml_adapter)
            valid_params.update(disambiguation_params)
        except exceptions.NotEnoughParametersToGetPidProviderXMLError:
            raise
    return valid_params


def get_journal_q_expression(xml_adapter):
    q = Q()
    if xml_adapter.journal_issn_electronic:
        q |= Q(issn_electronic=xml_adapter.journal_issn_electronic)
    if xml_adapter.journal_issn_print:
        q |= Q(issn_print=xml_adapter.journal_issn_print)
    if not xml_adapter.journal_issn_electronic and not xml_adapter.journal_issn_print:
        raise exceptions.RequiredISSNErrorToGetPidProviderXMLError(
            _("Required Print or Electronic ISSN to identify XML {}").format(
                xml_adapter.pkg_name,
            )
        )
    return q


def get_pub_year_expression(xml_adapter):
    q = Q()
    if xml_adapter.article_pub_year:
        q |= Q(article_pub_year=xml_adapter.article_pub_year)
    if xml_adapter.pub_year:
        q |= Q(pub_year=xml_adapter.pub_year)
    if not xml_adapter.article_pub_year and not xml_adapter.pub_year:
        raise exceptions.RequiredPublicationYearErrorToGetPidProviderXMLError(
            _("Required issue or article publication year {}").format(
                xml_adapter.pkg_name,
            )
        )
    return q


def get_basic_params(xml_adapter):
    _params = dict(
        z_surnames=xml_adapter.z_surnames or None,
        z_collab=xml_adapter.z_collab or None,
    )
    if xml_adapter.main_doi:
        _params["main_doi__iexact"] = xml_adapter.main_doi
    _params["elocation_id__iexact"] = xml_adapter.elocation_id
    return _params


def get_issue_params(xml_adapter, filter_by_issue=False, aop_version=False):
    _params = {}
    if aop_version:
        _params["volume__isnull"] = True
        _params["number__isnull"] = True
        _params["suppl__isnull"] = True
    elif filter_by_issue:
        _params["volume__iexact"] = xml_adapter.volume
        _params["number__iexact"] = xml_adapter.number
        _params["suppl__iexact"] = xml_adapter.suppl
        _params["fpage__iexact"] = xml_adapter.fpage
        _params["fpage_seq__iexact"] = xml_adapter.fpage_seq
        _params["lpage__iexact"] = xml_adapter.lpage
    return _params


def get_disambiguation_params(xml_adapter):
    _params = {}
    if xml_adapter.z_links:
        _params["z_links"] = xml_adapter.z_links
    elif xml_adapter.z_partial_body:
        _params["z_partial_body"] = xml_adapter.z_partial_body
    else:
        raise exceptions.NotEnoughParametersToGetPidProviderXMLError(
            _("No attribute enough for disambiguations {}").format(
                _params,
            )
        )
    return _params


def validate_query_params(query_params):
    _params = query_params

    if any(
        [
            _params.get("main_doi__iexact"),
            _params.get("fpage__iexact"),
            _params.get("elocation_id__iexact"),
        ]
    ):
        return True

    if not any(
        [
            _params.get("z_surnames"),
            _params.get("z_collab"),
        ]
    ):
        raise exceptions.RequiredAuthorErrorToGetPidProviderXMLError(
            _("Required collab or surname {}").format(
                _params,
            )
        )
    return True


def get_xml_adapter_data(xml_adapter):
    try:
        return xml_adapter.data
    except AttributeError:
        return dict(
            pkg_name=xml_adapter.sps_pkg_name,
            issn_print=xml_adapter.journal_issn_print,
            issn_electronic=xml_adapter.journal_issn_electronic,
            article_pub_year=xml_adapter.article_pub_year,
            pub_year=xml_adapter.pub_year,
            main_doi=xml_adapter.main_doi,
            elocation_id=xml_adapter.elocation_id,
            volume=xml_adapter.volume,
            number=xml_adapter.number,
            suppl=xml_adapter.suppl,
            fpage=xml_adapter.fpage,
            fpage_seq=xml_adapter.fpage_seq,
            lpage=xml_adapter.lpage,
            z_surnames=xml_adapter.z_surnames or None,
            z_collab=xml_adapter.z_collab or None,
            z_links=xml_adapter.z_links,
            z_partial_body=xml_adapter.z_partial_body,
        )