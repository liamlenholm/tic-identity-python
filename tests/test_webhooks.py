"""Tests for tic.webhooks — verify_signature with valid / invalid / expired payloads."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from tic.exceptions import TicWebhookError
from tic.models import (
    AuthCompletedData,
    EnrichmentCompletedData,
    EnrichmentFailedData,
    SignCompletedData,
    WebhookPayload,
)
from tic.webhooks import parse_webhook_data, verify_signature

SECRET = "whsec_test_secret_key"

SAMPLE_PAYLOAD = json.dumps(
    {
        "event": "auth.completed",
        "timestamp": "2026-06-15T12:01:00Z",
        "data": {"sessionId": "sess-001", "status": "complete"},
    }
)


def _make_signature(payload: str, timestamp: str, secret: str = SECRET) -> str:
    """Build a TIC webhook signature.

    HMAC-SHA256 over ``f"{timestamp}.{payload}"``, hex digest, prefixed
    with ``sha256=``. Stripe-style.
    """
    return (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            f"{timestamp}.{payload}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )


# ---------------------------------------------------------------------------
# Valid signatures
# ---------------------------------------------------------------------------


class TestSignatureScheme:
    """Pins the TIC webhook signature scheme.

    Stripe-style: the ``X-Ormeo-Signature`` header is ``sha256=<hex>``
    where ``<hex>`` is HMAC-SHA256 over ``f"{timestamp}.{body}"`` —
    not the raw body alone. The public C# / JS samples only show the
    HMAC computation step and don't make this composition clear.
    """

    def test_signature_is_stripe_style_with_timestamp_prefix(self):
        body = b'{"event":"auth.completed","timestamp":"2026-06-15T12:00:00Z","data":{"sessionId":"x"}}'
        secret = "whsec_x"
        ts = str(int(time.time()))

        msg = f"{ts}.{body.decode()}".encode()
        digest = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
        sig = f"sha256={digest}"

        result = verify_signature(body, ts, sig, secret)
        assert isinstance(result, WebhookPayload)

    def test_plain_hex_without_prefix_rejected(self):
        """A bare hex digest without ``sha256=`` is NOT TIC's format."""
        ts = str(int(time.time()))
        # Compute the right HMAC but omit the prefix.
        msg = f"{ts}.{SAMPLE_PAYLOAD}".encode()
        bare_hex = hmac.new(SECRET.encode(), msg, hashlib.sha256).hexdigest()
        with pytest.raises(TicWebhookError, match="Invalid signature"):
            verify_signature(SAMPLE_PAYLOAD, ts, bare_hex, SECRET)


class TestValidSignature:
    def test_valid_signature(self):
        ts = str(int(time.time()))
        sig = _make_signature(SAMPLE_PAYLOAD, ts)
        result = verify_signature(SAMPLE_PAYLOAD, ts, sig, SECRET)
        assert isinstance(result, WebhookPayload)
        assert result.event == "auth.completed"
        assert result.data["sessionId"] == "sess-001"

    def test_valid_signature_bytes_payload(self):
        ts = str(int(time.time()))
        payload_bytes = SAMPLE_PAYLOAD.encode("utf-8")
        sig = _make_signature(SAMPLE_PAYLOAD, ts)
        result = verify_signature(payload_bytes, ts, sig, SECRET)
        assert isinstance(result, WebhookPayload)
        assert result.event == "auth.completed"

    def test_signature_case_insensitive(self):
        ts = str(int(time.time()))
        sig = _make_signature(SAMPLE_PAYLOAD, ts)
        # Uppercase the signature — verify_signature lower-cases both sides
        result = verify_signature(SAMPLE_PAYLOAD, ts, sig.upper(), SECRET)
        assert isinstance(result, WebhookPayload)

    def test_custom_max_age(self):
        ts = str(int(time.time()) - 200)
        sig = _make_signature(SAMPLE_PAYLOAD, ts)
        # Should pass with a generous max_age
        result = verify_signature(SAMPLE_PAYLOAD, ts, sig, SECRET, max_age_seconds=600)
        assert isinstance(result, WebhookPayload)


# ---------------------------------------------------------------------------
# Invalid signatures
# ---------------------------------------------------------------------------


class TestInvalidSignature:
    def test_wrong_secret(self):
        ts = str(int(time.time()))
        sig = _make_signature(SAMPLE_PAYLOAD, ts, secret="wrong-secret")
        with pytest.raises(TicWebhookError, match="Invalid signature"):
            verify_signature(SAMPLE_PAYLOAD, ts, sig, SECRET)

    def test_tampered_payload(self):
        ts = str(int(time.time()))
        sig = _make_signature(SAMPLE_PAYLOAD, ts)
        tampered = SAMPLE_PAYLOAD.replace("sess-001", "sess-HACKED")
        with pytest.raises(TicWebhookError, match="Invalid signature"):
            verify_signature(tampered, ts, sig, SECRET)

    def test_tampered_timestamp(self):
        """Timestamp is part of the HMAC input, so tampering breaks it."""
        ts = str(int(time.time()))
        sig = _make_signature(SAMPLE_PAYLOAD, ts)
        wrong_ts = str(int(ts) + 1)
        with pytest.raises(TicWebhookError, match="Invalid signature"):
            verify_signature(SAMPLE_PAYLOAD, wrong_ts, sig, SECRET)

    def test_garbage_signature(self):
        ts = str(int(time.time()))
        with pytest.raises(TicWebhookError, match="Invalid signature"):
            verify_signature(SAMPLE_PAYLOAD, ts, "sha256=deadbeef", SECRET)


# ---------------------------------------------------------------------------
# Expired / future timestamps
# ---------------------------------------------------------------------------


class TestTimestampValidation:
    def test_expired_timestamp(self):
        old_ts = str(int(time.time()) - 600)
        sig = _make_signature(SAMPLE_PAYLOAD, old_ts)
        with pytest.raises(TicWebhookError, match="Timestamp too old"):
            verify_signature(SAMPLE_PAYLOAD, old_ts, sig, SECRET)

    def test_future_timestamp(self):
        future_ts = str(int(time.time()) + 120)
        sig = _make_signature(SAMPLE_PAYLOAD, future_ts)
        with pytest.raises(TicWebhookError, match="Timestamp is in the future"):
            verify_signature(SAMPLE_PAYLOAD, future_ts, sig, SECRET)

    def test_invalid_timestamp_string(self):
        sig = _make_signature(SAMPLE_PAYLOAD, "0")
        with pytest.raises(TicWebhookError, match="Invalid timestamp"):
            verify_signature(SAMPLE_PAYLOAD, "not-a-number", sig, SECRET)

    def test_none_timestamp(self):
        with pytest.raises(TicWebhookError, match="Invalid timestamp"):
            verify_signature(SAMPLE_PAYLOAD, None, "sha256=abc", SECRET)  # type: ignore[arg-type]

    def test_boundary_max_age(self):
        """Timestamp exactly at the boundary should still be valid (age == max_age is NOT > max_age)."""
        boundary_ts = str(int(time.time()) - 300)
        sig = _make_signature(SAMPLE_PAYLOAD, boundary_ts)
        # age == 300 and max_age_seconds == 300 → 300 > 300 is False → should pass
        result = verify_signature(
            SAMPLE_PAYLOAD, boundary_ts, sig, SECRET, max_age_seconds=300
        )
        assert isinstance(result, WebhookPayload)

    def test_just_past_max_age(self):
        """Timestamp one second past the limit should fail."""
        past_ts = str(int(time.time()) - 301)
        sig = _make_signature(SAMPLE_PAYLOAD, past_ts)
        with pytest.raises(TicWebhookError, match="Timestamp too old"):
            verify_signature(SAMPLE_PAYLOAD, past_ts, sig, SECRET, max_age_seconds=300)

    def test_future_within_tolerance(self):
        """Timestamps up to 60s in the future are tolerated."""
        ts = str(int(time.time()) + 30)
        sig = _make_signature(SAMPLE_PAYLOAD, ts)
        result = verify_signature(SAMPLE_PAYLOAD, ts, sig, SECRET)
        assert isinstance(result, WebhookPayload)


# ---------------------------------------------------------------------------
# parse_webhook_data
# ---------------------------------------------------------------------------


class TestParseWebhookData:
    def test_auth_completed(self):
        payload = WebhookPayload(
            event="auth.completed",
            timestamp="2026-06-15T12:00:00Z",
            data={
                "sessionId": "sess-001",
                "status": "complete",
                "provider": "bankid",
                "user": {
                    "personalNumber": "199001011234",
                    "givenName": "Anna",
                    "surname": "Svensson",
                },
                "state": "abc",
            },
        )
        result = parse_webhook_data(payload)
        assert isinstance(result, AuthCompletedData)
        assert result.session_id == "sess-001"
        assert result.user.given_name == "Anna"

    def test_sign_completed(self):
        payload = WebhookPayload(
            event="sign.completed",
            timestamp="2026-06-15T12:00:00Z",
            data={
                "sessionId": "sess-002",
                "status": "complete",
                "provider": "bankid",
                "user": {
                    "personalNumber": "199001011234",
                    "givenName": "Erik",
                    "surname": "Johansson",
                },
                "signature": {"value": "sig-val", "ocspResponse": "ocsp-val"},
            },
        )
        result = parse_webhook_data(payload)
        assert isinstance(result, SignCompletedData)
        assert result.signature.value == "sig-val"

    def test_enrichment_completed(self):
        payload = WebhookPayload(
            event="enrichment.completed",
            timestamp="2026-06-15T12:00:00Z",
            data={
                "enrichmentId": "enr-001",
                "sessionId": "sess-003",
                "status": "completed",
                "secureUrl": "https://id.tic.io/enrichment/data/token-abc",
                "secureUrlExpiresAtUtc": "2026-06-15T12:30:00Z",
                "state": "my-state",
            },
        )
        result = parse_webhook_data(payload)
        assert isinstance(result, EnrichmentCompletedData)
        assert result.enrichment_id == "enr-001"
        assert result.secure_url == "https://id.tic.io/enrichment/data/token-abc"
        assert result.state == "my-state"

    def test_enrichment_failed(self):
        payload = WebhookPayload(
            event="enrichment.failed",
            timestamp="2026-06-15T12:00:00Z",
            data={
                "enrichmentId": "enr-002",
                "sessionId": "sess-004",
                "status": "failed",
                "error": "Session too old",
            },
        )
        result = parse_webhook_data(payload)
        assert isinstance(result, EnrichmentFailedData)
        assert result.error == "Session too old"

    def test_unknown_event_returns_dict(self):
        payload = WebhookPayload(
            event="some.future.event",
            timestamp="2026-06-15T12:00:00Z",
            data={"foo": "bar"},
        )
        result = parse_webhook_data(payload)
        assert isinstance(result, dict)
        assert result == {"foo": "bar"}
