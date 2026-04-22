"""TIC Identity Python client — BankID authentication and digital signing via id.tic.io."""

__version__ = "0.1.0"

from .client import RateLimitInfo, TicClient
from .constants import (
    BASE_URL,
    Environment,
    ErrorCode,
    HintCode,
    SessionStatus as SessionStatusEnum,
    WebhookEvent,
    WebhookHeader,
)
from .data import (
    CompanyCreditData,
    CompanyCreditResponse,
    CompanyLookupData,
    CompanyLookupResponse,
    SigningAuthorityAnalysis,
    SigningAuthorityResponse,
)
from .enrichment import (
    EnrichmentData,
    EnrichmentResponse,
    EnrichmentStatus,
    EnrichmentType,
    EnrichmentTypeInfo,
    SparData,
)
from .exceptions import TicAPIError, TicError, TicHubError, TicWebhookError
from .helpers import bankid_autostart_url, hosted_login_url, parse_callback
from .hub import TicHub
from .models import (
    AuthCompletedData,
    AuthSession,
    AuthStartRequest,
    AuthStatusResponse,
    CollectResult,
    Completed,
    EnrichmentCompletedData,
    EnrichmentFailedData,
    ExtendResult,
    Failed,
    IpInfo,
    IpIntelligence,
    LocalizedMessage,
    OrderRegenerated,
    QRCodeResult,
    RiskAssessment,
    SessionStatus,
    Signature,
    SignCompletedData,
    SignStartRequest,
    StatusChanged,
    SubscribeResponse,
    TimeoutWarning,
    UsageStats,
    User,
    WebhookPayload,
)
from .qr import generate_qr_data
from .webhooks import parse_webhook_data, verify_signature

__all__ = [
    "__version__",
    # Client
    "TicClient",
    "TicHub",
    "RateLimitInfo",
    # Exceptions
    "TicAPIError",
    "TicError",
    "TicHubError",
    "TicWebhookError",
    # Constants / Enums
    "Environment",
    "BASE_URL",
    "ErrorCode",
    "HintCode",
    "SessionStatusEnum",
    "WebhookEvent",
    "WebhookHeader",
    # Auth models
    "AuthSession",
    "AuthStartRequest",
    "CollectResult",
    "ExtendResult",
    "QRCodeResult",
    "SessionStatus",
    "SignStartRequest",
    "UsageStats",
    "User",
    "Signature",
    "LocalizedMessage",
    # Hub models
    "AuthStatusResponse",
    "Completed",
    "Failed",
    "OrderRegenerated",
    "StatusChanged",
    "SubscribeResponse",
    "TimeoutWarning",
    # Webhook models
    "AuthCompletedData",
    "EnrichmentCompletedData",
    "EnrichmentFailedData",
    "SignCompletedData",
    "WebhookPayload",
    "IpInfo",
    "IpIntelligence",
    "RiskAssessment",
    # Webhook helpers
    "parse_webhook_data",
    "verify_signature",
    # Utilities
    "bankid_autostart_url",
    "generate_qr_data",
    "hosted_login_url",
    "parse_callback",
    # Enrichment
    "EnrichmentData",
    "EnrichmentResponse",
    "EnrichmentStatus",
    "EnrichmentType",
    "EnrichmentTypeInfo",
    "SparData",
    # Data Verification
    "CompanyCreditData",
    "CompanyCreditResponse",
    "CompanyLookupData",
    "CompanyLookupResponse",
    "SigningAuthorityAnalysis",
    "SigningAuthorityResponse",
]
