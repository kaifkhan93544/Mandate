import hashlib
import hmac
import json

from .config import SIGNING_SECRET


def create_signature(data: dict) -> str:
    """Create an HMAC-SHA256 signature for a mandate."""

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
    """Verify that a mandate has not been changed."""

    expected_signature = create_signature(data)

    return hmac.compare_digest(
        expected_signature,
        signature
    )
