import hashlib
import hmac
import json

from .config import SIGNING_SECRET


def create_signature(data: dict) -> str:
    message = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")

    return hmac.new(
        SIGNING_SECRET,
        message,
        hashlib.sha256
    ).hexdigest()


def verify_signature(data: dict, signature: str) -> bool:
    expected_signature = create_signature(data)

    return hmac.compare_digest(
        expected_signature,
        signature
    )
