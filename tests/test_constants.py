"""Tests for tic.constants — StrEnum values, properties, and membership."""

from __future__ import annotations

from tic.constants import (
    BASE_URL,
    ErrorCode,
    HintCode,
    SessionStatus,
    WebhookEvent,
    WebhookHeader,
)


# ---------------------------------------------------------------------------
# HintCode
# ---------------------------------------------------------------------------


class TestHintCode:
    def test_pending_values(self):
        assert HintCode.OUTSTANDING_TRANSACTION == "outstandingTransaction"
        assert HintCode.NO_CLIENT == "noClient"
        assert HintCode.STARTED == "started"
        assert HintCode.USER_SIGN == "userSign"
        assert HintCode.USER_MRTD == "userMrtd"

    def test_failed_values(self):
        assert HintCode.EXPIRED_TRANSACTION == "expiredTransaction"
        assert HintCode.CERTIFICATE_ERR == "certificateErr"
        assert HintCode.USER_CANCEL == "userCancel"
        assert HintCode.CANCELLED == "cancelled"
        assert HintCode.START_FAILED == "startFailed"
        assert HintCode.ALREADY_IN_PROGRESS == "alreadyInProgress"

    def test_is_pending_true_for_pending_codes(self):
        pending_codes = [
            HintCode.OUTSTANDING_TRANSACTION,
            HintCode.NO_CLIENT,
            HintCode.STARTED,
            HintCode.USER_SIGN,
            HintCode.USER_MRTD,
        ]
        for code in pending_codes:
            assert code.is_pending is True, f"{code} should be pending"
            assert code.is_failed is False, f"{code} should not be failed"

    def test_is_failed_true_for_failed_codes(self):
        failed_codes = [
            HintCode.EXPIRED_TRANSACTION,
            HintCode.CERTIFICATE_ERR,
            HintCode.USER_CANCEL,
            HintCode.CANCELLED,
            HintCode.START_FAILED,
            HintCode.ALREADY_IN_PROGRESS,
        ]
        for code in failed_codes:
            assert code.is_failed is True, f"{code} should be failed"
            assert code.is_pending is False, f"{code} should not be pending"

    def test_is_pending_and_is_failed_are_mutually_exclusive(self):
        for code in HintCode:
            assert not (code.is_pending and code.is_failed), (
                f"{code} cannot be both pending and failed"
            )

    def test_every_hint_code_is_either_pending_or_failed(self):
        for code in HintCode:
            assert code.is_pending or code.is_failed, (
                f"{code} should be either pending or failed"
            )

    def test_hint_code_is_str(self):
        assert isinstance(HintCode.STARTED, str)
        assert HintCode.STARTED == "started"

    def test_hint_code_from_string(self):
        code = HintCode("outstandingTransaction")
        assert code is HintCode.OUTSTANDING_TRANSACTION


# ---------------------------------------------------------------------------
# SessionStatus
# ---------------------------------------------------------------------------


class TestSessionStatus:
    def test_values(self):
        assert SessionStatus.PENDING == "pending"
        assert SessionStatus.COMPLETE == "complete"
        assert SessionStatus.FAILED == "failed"
        assert SessionStatus.CANCELLED == "cancelled"

    def test_member_count(self):
        assert len(SessionStatus) == 4

    def test_is_str(self):
        assert isinstance(SessionStatus.PENDING, str)

    def test_from_string(self):
        assert SessionStatus("complete") is SessionStatus.COMPLETE


# ---------------------------------------------------------------------------
# ErrorCode
# ---------------------------------------------------------------------------


class TestErrorCode:
    def test_authentication_errors(self):
        assert ErrorCode.INVALID_API_KEY == "invalid_api_key"
        assert ErrorCode.API_KEY_DISABLED == "api_key_disabled"
        assert ErrorCode.TENANT_INACTIVE == "tenant_inactive"

    def test_session_errors(self):
        assert ErrorCode.SESSION_NOT_FOUND == "session_not_found"
        assert ErrorCode.SESSION_EXPIRED == "session_expired"
        assert ErrorCode.ALREADY_EXTENDED == "already_extended"
        assert ErrorCode.QR_NOT_AVAILABLE == "qr_not_available"

    def test_validation_errors(self):
        assert ErrorCode.PROVIDER_NOT_ENABLED == "provider_not_enabled"
        assert ErrorCode.INVALID_CALLBACK_URL == "invalid_callback_url"
        assert ErrorCode.INVALID_WEBHOOK_URL == "invalid_webhook_url"
        assert ErrorCode.MISSING_VISIBLE_DATA == "missing_visible_data"

    def test_usage_limit_errors(self):
        assert ErrorCode.LIMIT_EXCEEDED == "limit_exceeded"

    def test_enrichment_errors(self):
        assert ErrorCode.ENRICHMENT_NOT_ENABLED == "enrichment_not_enabled"
        assert ErrorCode.NO_VALID_TYPES == "no_valid_types"
        assert ErrorCode.SESSION_NOT_COMPLETED == "session_not_completed"
        assert ErrorCode.NO_PERSONAL_NUMBER == "no_personal_number"
        assert ErrorCode.URL_EXPIRED == "url_expired"

    def test_from_string(self):
        assert ErrorCode("session_not_found") is ErrorCode.SESSION_NOT_FOUND

    def test_is_str(self):
        assert isinstance(ErrorCode.INVALID_API_KEY, str)


# ---------------------------------------------------------------------------
# WebhookEvent
# ---------------------------------------------------------------------------


class TestWebhookEvent:
    def test_values(self):
        assert WebhookEvent.AUTH_COMPLETED == "auth.completed"
        assert WebhookEvent.SIGN_COMPLETED == "sign.completed"
        assert WebhookEvent.ENRICHMENT_COMPLETED == "enrichment.completed"
        assert WebhookEvent.ENRICHMENT_FAILED == "enrichment.failed"

    def test_member_count(self):
        assert len(WebhookEvent) == 4

    def test_from_string(self):
        assert WebhookEvent("auth.completed") is WebhookEvent.AUTH_COMPLETED


# ---------------------------------------------------------------------------
# WebhookHeader
# ---------------------------------------------------------------------------


class TestWebhookHeader:
    def test_values(self):
        assert WebhookHeader.SIGNATURE == "X-Ormeo-Signature"
        assert WebhookHeader.TIMESTAMP == "X-Ormeo-Timestamp"
        assert WebhookHeader.SESSION_ID == "X-Ormeo-Session-Id"

    def test_member_count(self):
        # Only three headers sent on the wire; the event type lives in
        # the request body, not a header.
        assert len(WebhookHeader) == 3

    def test_no_event_header(self):
        """The event type is in the body, not a header.

        Read it from :attr:`WebhookPayload.event` after
        :func:`verify_signature`.
        """
        assert not hasattr(WebhookHeader, "EVENT")

    def test_usable_as_dict_key(self):
        headers = {
            WebhookHeader.SIGNATURE: "abc123",
            WebhookHeader.TIMESTAMP: "1700000000",
        }
        assert headers["X-Ormeo-Signature"] == "abc123"


# ---------------------------------------------------------------------------
# BASE_URL
# ---------------------------------------------------------------------------


class TestBaseUrl:
    def test_value(self):
        assert BASE_URL == "https://id.tic.io"

    def test_is_valid_url(self):
        assert BASE_URL.startswith("https://")
