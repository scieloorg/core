import logging
import re
from urllib.parse import urlparse

from argon2.exceptions import HashingError
from argon2.low_level import Type, hash_secret_raw
from curl_cffi.requests.exceptions import RequestException

logger = logging.getLogger(__name__)

DIFFICULTY = 13
ATTEMPT_LIMIT = 200_000
POW_TOKEN = re.compile(r"""data-pow=["']([^"']+)["']""")

_cookies = {}


def _accepted(digest, difficulty=DIFFICULTY):
    zero_nibbles = difficulty // 8
    if not digest.startswith("0" * zero_nibbles):
        return False
    shift = ((zero_nibbles + 1) * 8) - difficulty
    return (int(digest[zero_nibbles], 16) & (0xFF >> shift)) == 0


def solve(pow_token, difficulty=DIFFICULTY):
    """Solve the Argon2id proof of work published by Bunny Shield."""
    user_key, challenge, *_ = pow_token.split("#")
    for counter in range(ATTEMPT_LIMIT):
        digest = hash_secret_raw(
            secret=f"{challenge}{counter}".encode(),
            salt=user_key.encode(),
            time_cost=2,
            memory_cost=512,
            parallelism=1,
            hash_len=32,
            type=Type.ID,
        ).hex()
        if _accepted(digest, difficulty):
            return f"{pow_token}#{counter}"
    raise ValueError(f"Bunny Shield proof of work exceeded {ATTEMPT_LIMIT} attempts")


def _challenge(response):
    if response.status_code != 403:
        return None
    content = response.content
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="ignore")
    match = POW_TOKEN.search(content or "")
    return match.group(1) if match else None


def _save_cookie(session, host):
    for cookie in session.cookies.jar:
        if cookie.name == "bunny_shield" and cookie.value:
            _cookies[host] = cookie.value
            break


def get(session, url):
    """
    GET a URL and transparently solve Bunny Shield when its public proof of
    work challenge is returned. Cookies are reused by host in this process.
    """
    host = (urlparse(url).hostname or "").lower()
    if host in _cookies:
        session.cookies.set("bunny_shield", _cookies[host], domain=host)

    response = session.get(url)
    pow_token = _challenge(response)
    if not pow_token:
        return response

    try:
        answer = solve(pow_token)
        origin = f"{urlparse(response.url).scheme}://{urlparse(response.url).netloc}"
        verification = session.post(
            f"{origin}/.bunny-shield/verify-pow",
            data=b"",
            headers={
                "Content-Type": "application/json",
                "BunnyShield-Challenge-Response": answer,
            },
            allow_redirects=False,
        )
        verification.raise_for_status()
    except (RequestException, ValueError, HashingError) as error:
        logger.warning("Bunny Shield verification failed for %s: %s", url, error)
        return response

    _save_cookie(session, host)
    return session.get(response.url)
