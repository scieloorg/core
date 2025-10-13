import logging
import time

import jwt
from django.conf import settings


def issue_jwt_for_flask(sub="service:django", claims=None):
    now = int(time.time())
    payload = {
        "iss": settings.JWT_ISS,
        "aud": settings.JWT_AUD,
        "iat": now,
        "nbf": now,
        "exp": now + settings.JWT_EXP_SECONDS,
        "sub": sub,
    }
    if claims:
        payload.update(claims)
    
    private_key = get_jwt_private_key()
    
    if not private_key:
        return None
    
    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"alg": "RS256", "typ": "JWT"},
    )
    return token

def get_jwt_private_key():
    try:
        with open(settings.JWT_PRIVATE_KEY_PATH, "rb") as f:
            return f.read()
    except (FileNotFoundError, IOError):
        logging.error("JWT_PRIVATE_KEY_PATH not found")
        return None
