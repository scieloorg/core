import logging
import re

import requests
from django.contrib.auth import get_user_model
from langcodes import standardize_tag, tag_is_valid
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from urllib3.util import Retry

from config.settings.base import FETCH_DATA_TIMEOUT

logger = logging.getLogger(__name__)
User = get_user_model()


def language_iso(code):
    code = re.split(r"-|_", code)[0] if code else ""
    if tag_is_valid(code):
        return standardize_tag(code)
    return ""


class RetryableError(Exception):
    """Recoverable error without having to modify the data state on the client
    side, e.g. timeouts, errors from network partitioning, etc.
    """


class NonRetryableError(Exception):
    """Recoverable error without having to modify the data state on the client
    side, e.g. timeouts, errors from network partitioning, etc.
    """


@retry(
    retry=retry_if_exception_type(RetryableError),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    stop=stop_after_attempt(5),
)
def fetch_data(url, headers=None, json=False, timeout=FETCH_DATA_TIMEOUT, verify=True):
    """
    Get the resource with HTTP
    Retry: Wait 2^x * 1 second between each retry starting with 4 seconds,
           then up to 10 seconds, then 10 seconds afterwards
    Args:
        url: URL address
        headers: HTTP headers
        json: True|False
        verify: Verify the SSL.
    Returns:
        Return a requests.response object.
    Except:
        Raise a RetryableError to retry.
    """

    try:
        response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        logger.error("Erro fetching the content: %s, retry..., erro: %s" % (url, exc))
        raise RetryableError(exc) from exc
    except (
        requests.exceptions.InvalidSchema,
        requests.exceptions.MissingSchema,
        requests.exceptions.InvalidURL,
    ) as exc:
        logger.error(
            "Erro fetching the content: %s, not retryable..., erro: %s" % (url, exc)
        )
        raise NonRetryableError(exc) from exc
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if 400 <= exc.response.status_code < 500:
            logger.error(
                "Erro fetching the content: %s, not retryable..., erro: %s" % (url, exc)
            )
            raise NonRetryableError(exc) from exc
        elif 500 <= exc.response.status_code < 600:
            raise RetryableError(exc) from exc
        else:
            logger.error("Erro fetching the content: %s, erro: %s" % (url, exc))
            raise

    return response.content if not json else response.json()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user_id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


def formated_date_api_params(query_params):
    formated_date = {}
    for date_param, filter_key in [
        ("from_date_created", "created__gte"),
        ("until_date_created", "created__lte"),
        ("from_date_updated", "updated__gte"),
        ("until_date_updated", "updated__lte"),
    ]:
        if data_value := query_params.get(date_param):
            try:
                formated_date.update({filter_key: data_value.replace("/", "-")})
            except (ValueError, AttributeError):
                continue
    return formated_date
