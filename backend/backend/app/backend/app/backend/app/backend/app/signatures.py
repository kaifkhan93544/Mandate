import hashlib
import hmac
import json

from .config import SIGNING_SECRET


def sign_mandate(data: dict) -> str:
    payload = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":")
    ).encode()

    return hmac.new(
        SIGNING_SECRET,
        payload,
        hashlib.sha256
    ).hexdigest()


def verify_mandate(data: dict, signature: str) -> bool:
    return hmac.compare_digest(
        sign_mandate(data),
        signature
    )
