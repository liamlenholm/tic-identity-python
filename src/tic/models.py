from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def to_api(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Self:
        return cls.model_validate(data)


# --- Request models ---


class AuthStartRequest(CamelModel):
    end_user_ip: str
    user_agent: str | None = None
    personal_number: str | None = None
    callback_url: str | None = None
    webhook_url: str | None = None
    state: str | None = None


class SignStartRequest(AuthStartRequest):
    user_visible_data: str
    user_visible_data_format: str | None = None
    user_non_visible_data: str | None = None


# --- Session models ---


class AuthSession(CamelModel):
    session_id: str
    provider: str
    order_ref: str
    auto_start_token: str
    qr_start_token: str
    qr_start_secret: str
    subscription_token: str
    end_user_ip: str | None = None
    session_expires_at: datetime


class User(CamelModel):
    personal_number: str
    given_name: str
    surname: str
    name: str | None = None
    external_subject_id: str | None = None
    provider: str | None = None


class Signature(CamelModel):
    value: str
    ocsp_response: str
    signed_data: str | None = None


class CollectResult(CamelModel):
    session_id: str
    status: str
    token: str | None = None
    user: User | None = None
    signature: Signature | None = None
    completed_at: datetime | None = None


class SessionStatus(CamelModel):
    session_id: str
    status: str
    hint_code: str | None = None
    message: str | None = None
    message_en: str | None = None
    error: str | None = None
    order_count: int | None = None
    max_orders: int | None = None
    session_expires_in_seconds: int | None = None


class QRCodeResult(CamelModel):
    qr_data: str
    valid_for_seconds: int
    order_age: int | None = None


class ExtendResult(CamelModel):
    extended: bool
    error: str | None = None
    new_expires_at: datetime | None = None
    session_expires_in_seconds: int | None = None


class UsageLimits(CamelModel):
    authentications_per_month: int | None = None
    signings_per_month: int | None = None
    enrichments_per_month: int | None = None


class UsageStats(CamelModel):
    year: int
    month: int
    provider: str
    authentications_started: int
    authentications_completed: int
    authentications_failed: int
    signings_started: int | None = None
    signings_completed: int | None = None
    signings_failed: int | None = None
    enrichments_requested: int | None = None
    enrichments_delivered: int | None = None
    limits: UsageLimits | None = None


# --- SignalR hub event models ---


class StatusChanged(CamelModel):
    status: str
    hint_code: str | None = None
    message: str | None = None
    message_en: str | None = None


class Completed(CamelModel):
    session_id: str
    status: str
    user: User
    completed_at: datetime | None = None


class Failed(CamelModel):
    hint_code: str
    message: str | None = None
    message_en: str | None = None


class TimeoutWarning(CamelModel):
    seconds_remaining: int
    can_extend: bool


class OrderRegenerated(CamelModel):
    order_count: int
    max_orders: int
    session_expires_in_seconds: int


# --- SignalR hub response models ---


class SubscribeResponse(CamelModel):
    session_id: str
    provider: str
    status: str
    auto_start_token: str
    session_expires_at: datetime


class AuthStatusResponse(CamelModel):
    session_id: str
    status: str
    hint_code: str | None = None
    message: str | None = None
    message_en: str | None = None
    order_count: int | None = None
    max_orders: int | None = None
    session_expires_in_seconds: int | None = None


# --- Webhook models ---


class WebhookPayload(BaseModel):
    event: str
    timestamp: datetime
    data: dict[str, Any]


class AuthCompletedData(CamelModel):
    session_id: str
    status: str
    provider: str
    user: User
    state: str | None = None
    ip_intelligence: IpIntelligence | None = None


class SignCompletedData(CamelModel):
    session_id: str
    status: str
    provider: str
    user: User
    signature: Signature
    state: str | None = None
    ip_intelligence: IpIntelligence | None = None


class EnrichmentCompletedData(CamelModel):
    enrichment_id: str
    session_id: str
    status: str
    secure_url: str
    expires_at_utc: datetime | None = None
    state: str | None = None


class EnrichmentFailedData(CamelModel):
    enrichment_id: str
    session_id: str
    status: str
    error: str | None = None
    state: str | None = None


# --- IP intelligence models ---


class IpInfo(CamelModel):
    ip_address: str
    country_code: str | None = None
    country_name: str | None = None
    isp: str | None = None
    usage_type: str | None = None
    is_tor: bool = False
    is_likely_vpn: bool = False
    confidence_score: int | None = None


class RiskAssessment(CamelModel):
    level: str
    score: int
    indicators: list[str] = []


class IpIntelligence(CamelModel):
    initiating_ip: IpInfo | None = None
    device_ip: IpInfo | None = None
    overall_risk: RiskAssessment | None = None
    enriched_at_utc: datetime | None = None


# --- Messages ---


class HintCodeMapping(CamelModel):
    rfa: str
    variants: list[str] = []


class MessagesResponse(CamelModel):
    language: str
    messages: dict[str, str]
    hint_code_mapping: dict[str, HintCodeMapping] = {}


# Deprecated: use MessagesResponse instead
class LocalizedMessage(CamelModel):
    hint_code: str
    message: str
