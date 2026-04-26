from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

from .constants import WebhookEvent, WebhookHeader
from .exceptions import TicWebhookError
from .models import (
    AuthCompletedData,
    EnrichmentCompletedData,
    EnrichmentFailedData,
    SignCompletedData,
    WebhookPayload,
)

HEADER_SIGNATURE = WebhookHeader.SIGNATURE
HEADER_TIMESTAMP = WebhookHeader.TIMESTAMP
HEADER_SESSION_ID = WebhookHeader.SESSION_ID


def verify_signature(
    payload: str | bytes,
    timestamp: str,
    signature: str,
    secret: str,
    *,
    max_age_seconds: int = 300,
) -> WebhookPayload:
    """Verify a TIC Identity webhook signature and return the parsed payload.

    Raises TicWebhookError if verification fails.
    """
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")

    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        raise TicWebhookError("Invalid timestamp")

    age = int(time.time()) - ts
    if age > max_age_seconds:
        raise TicWebhookError(f"Timestamp too old ({age}s > {max_age_seconds}s)")
    if age < -60:
        raise TicWebhookError("Timestamp is in the future")

    sign_payload = f"{timestamp}.{payload}"
    expected = (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            sign_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(signature.lower(), expected.lower()):
        raise TicWebhookError("Invalid signature")

    data = json.loads(payload)
    return WebhookPayload.model_validate(data)


def parse_webhook_data(
    payload: WebhookPayload,
) -> (
    AuthCompletedData
    | SignCompletedData
    | EnrichmentCompletedData
    | EnrichmentFailedData
    | dict[str, Any]
):
    """Parse the untyped webhook data into a typed model based on event type."""
    if payload.event == WebhookEvent.AUTH_COMPLETED:
        return AuthCompletedData.from_api(payload.data)
    if payload.event == WebhookEvent.SIGN_COMPLETED:
        return SignCompletedData.from_api(payload.data)
    if payload.event == WebhookEvent.ENRICHMENT_COMPLETED:
        return EnrichmentCompletedData.from_api(payload.data)
    if payload.event == WebhookEvent.ENRICHMENT_FAILED:
        return EnrichmentFailedData.from_api(payload.data)
    return payload.data
