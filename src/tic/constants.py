"""Constants and enumerations for the TIC Identity API.

Provides typed enums for BankID hint codes, session statuses, API error codes,
webhook events, webhook headers, and environment base URLs. All values are
sourced from the official documentation at https://id.tic.io/docs.
"""

from __future__ import annotations

from enum import StrEnum


class HintCode(StrEnum):
    """BankID hint codes returned during session polling.

    Pending hint codes indicate the session is still in progress.
    Failed hint codes indicate the session has ended unsuccessfully.
    """

    # --- Pending (status: pending) ---

    OUTSTANDING_TRANSACTION = "outstandingTransaction"
    """Waiting for the user to open the BankID app."""

    NO_CLIENT = "noClient"
    """No BankID client is responding."""

    STARTED = "started"
    """The BankID app has been launched; searching for a BankID."""

    USER_SIGN = "userSign"
    """The user is authenticating (entering security code)."""

    USER_MRTD = "userMrtd"
    """The user is scanning an ID document."""

    # --- Failed (status: failed) ---

    EXPIRED_TRANSACTION = "expiredTransaction"
    """The BankID session timed out without a response."""

    CERTIFICATE_ERR = "certificateErr"
    """The user's BankID is invalid, revoked, or too old."""

    USER_CANCEL = "userCancel"
    """The user cancelled the operation in the BankID app."""

    CANCELLED = "cancelled"
    """The session was cancelled (e.g. via API)."""

    START_FAILED = "startFailed"
    """The BankID app could not be started or QR code could not be read."""

    ALREADY_IN_PROGRESS = "alreadyInProgress"
    """Another authentication is already in progress for this personal number."""

    @property
    def is_pending(self) -> bool:
        """Return True if this hint code indicates a pending (in-progress) session."""
        return self in _PENDING_HINT_CODES

    @property
    def is_failed(self) -> bool:
        """Return True if this hint code indicates a failed session."""
        return self in _FAILED_HINT_CODES


_PENDING_HINT_CODES = frozenset(
    {
        HintCode.OUTSTANDING_TRANSACTION,
        HintCode.NO_CLIENT,
        HintCode.STARTED,
        HintCode.USER_SIGN,
        HintCode.USER_MRTD,
    }
)

_FAILED_HINT_CODES = frozenset(
    {
        HintCode.EXPIRED_TRANSACTION,
        HintCode.CERTIFICATE_ERR,
        HintCode.USER_CANCEL,
        HintCode.CANCELLED,
        HintCode.START_FAILED,
        HintCode.ALREADY_IN_PROGRESS,
    }
)


class SessionStatus(StrEnum):
    """Possible statuses of a TIC Identity session."""

    PENDING = "pending"
    """The session is waiting for the user to complete the action."""

    COMPLETE = "complete"
    """The session finished successfully."""

    FAILED = "failed"
    """The session failed (see hint code for reason)."""

    CANCELLED = "cancelled"
    """The session was cancelled."""


class ErrorCode(StrEnum):
    """API error codes returned in the ``error`` field of error responses.

    Grouped logically by category: authentication, session, validation,
    usage limits, and enrichment.
    """

    # --- Authentication ---

    INVALID_API_KEY = "invalid_api_key"
    """The API key is invalid or missing."""

    API_KEY_DISABLED = "api_key_disabled"
    """The API key has been deactivated."""

    TENANT_INACTIVE = "tenant_inactive"
    """The tenant is not active."""

    # --- Session ---

    SESSION_NOT_FOUND = "session_not_found"
    """The session does not exist or has expired."""

    SESSION_EXPIRED = "session_expired"
    """The session has expired."""

    ALREADY_EXTENDED = "already_extended"
    """The session has already been extended once."""

    QR_NOT_AVAILABLE = "qr_not_available"
    """QR code is not available for this session."""

    # --- Validation ---

    PROVIDER_NOT_ENABLED = "provider_not_enabled"
    """The identity provider is not enabled for this tenant."""

    INVALID_CALLBACK_URL = "invalid_callback_url"
    """The callback URL is not on the allowlist."""

    INVALID_WEBHOOK_URL = "invalid_webhook_url"
    """The webhook URL is not on the allowlist."""

    MISSING_VISIBLE_DATA = "missing_visible_data"
    """``userVisibleData`` is required for signing sessions."""

    # --- Usage limits ---

    LIMIT_EXCEEDED = "limit_exceeded"
    """Monthly authentication limit has been exceeded."""

    # --- Enrichment ---

    ENRICHMENT_NOT_ENABLED = "enrichment_not_enabled"
    """Enrichment is not enabled for this tenant."""

    NO_VALID_TYPES = "no_valid_types"
    """None of the requested enrichment types are configured."""

    SESSION_NOT_COMPLETED = "session_not_completed"
    """The session has not been completed yet."""

    NO_PERSONAL_NUMBER = "no_personal_number"
    """The session does not contain a personal number."""

    URL_EXPIRED = "url_expired"
    """The enrichment data URL has expired (30 min TTL)."""


class WebhookEvent(StrEnum):
    """Webhook event types sent by TIC Identity."""

    AUTH_COMPLETED = "auth.completed"
    """An authentication session completed successfully."""

    SIGN_COMPLETED = "sign.completed"
    """A signing session completed successfully."""

    ENRICHMENT_COMPLETED = "enrichment.completed"
    """Enrichment data is ready for retrieval."""

    ENRICHMENT_FAILED = "enrichment.failed"
    """Enrichment failed for the session."""


class WebhookHeader(StrEnum):
    """HTTP header names included in TIC Identity webhook requests."""

    SIGNATURE = "X-Ormeo-Signature"
    """HMAC-SHA256 signature of the request body."""

    TIMESTAMP = "X-Ormeo-Timestamp"
    """Unix timestamp when the webhook was sent."""

    EVENT = "X-Ormeo-Event"
    """The webhook event type (e.g. ``enrichment.completed``)."""

    SESSION_ID = "X-Ormeo-Session-Id"
    """The session ID associated with the webhook."""


class Environment(StrEnum):
    """TIC Identity API environment base URLs.

    TIC Identity uses a single domain; test vs. production behaviour
    is determined by the tenant's mode, not by the URL.
    """

    TEST = "https://id.tic.io"
    PRODUCTION = "https://id.tic.io"


BASE_URL: str = "https://id.tic.io"
