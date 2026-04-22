"""Tests for tic.models — from_api / to_api round-trip and edge cases."""

from __future__ import annotations

from datetime import datetime, timezone

from tic.models import (
    AuthCompletedData,
    AuthSession,
    AuthStartRequest,
    CollectResult,
    EnrichmentCompletedData,
    EnrichmentFailedData,
    ExtendResult,
    IpInfo,
    IpIntelligence,
    QRCodeResult,
    RiskAssessment,
    SessionStatus,
    SignCompletedData,
    SignStartRequest,
    Signature,
    UsageStats,
    User,
    WebhookPayload,
)


# ---------------------------------------------------------------------------
# AuthStartRequest.to_api
# ---------------------------------------------------------------------------


class TestAuthStartRequest:
    def test_to_api_required_only(self):
        req = AuthStartRequest(end_user_ip="192.168.1.1")
        assert req.to_api() == {"endUserIp": "192.168.1.1"}

    def test_to_api_all_fields(self):
        req = AuthStartRequest(
            end_user_ip="10.0.0.1",
            personal_number="199001011234",
            callback_url="https://example.com/cb",
            webhook_url="https://example.com/wh",
            state="abc123",
        )
        result = req.to_api()
        assert result == {
            "endUserIp": "10.0.0.1",
            "personalNumber": "199001011234",
            "callbackUrl": "https://example.com/cb",
            "webhookUrl": "https://example.com/wh",
            "state": "abc123",
        }

    def test_to_api_omits_none_fields(self):
        req = AuthStartRequest(end_user_ip="1.2.3.4", personal_number="199001011234")
        result = req.to_api()
        assert "callbackUrl" not in result
        assert "webhookUrl" not in result
        assert "state" not in result


# ---------------------------------------------------------------------------
# SignStartRequest.to_api
# ---------------------------------------------------------------------------


class TestSignStartRequest:
    def test_to_api_required_only(self):
        req = SignStartRequest(
            end_user_ip="192.168.1.1",
            user_visible_data="Sign this document",
        )
        assert req.to_api() == {
            "endUserIp": "192.168.1.1",
            "userVisibleData": "Sign this document",
        }

    def test_to_api_all_fields(self):
        req = SignStartRequest(
            end_user_ip="10.0.0.1",
            user_visible_data="Please sign the contract",
            user_visible_data_format="simpleMarkdownV1",
            user_non_visible_data="hidden-data-hash",
            personal_number="199001011234",
            callback_url="https://example.com/cb",
            webhook_url="https://example.com/wh",
            state="sign-state-1",
        )
        result = req.to_api()
        assert result == {
            "endUserIp": "10.0.0.1",
            "userVisibleData": "Please sign the contract",
            "userVisibleDataFormat": "simpleMarkdownV1",
            "userNonVisibleData": "hidden-data-hash",
            "personalNumber": "199001011234",
            "callbackUrl": "https://example.com/cb",
            "webhookUrl": "https://example.com/wh",
            "state": "sign-state-1",
        }

    def test_to_api_omits_none_optional_fields(self):
        req = SignStartRequest(
            end_user_ip="1.2.3.4",
            user_visible_data="test",
        )
        result = req.to_api()
        assert "userVisibleDataFormat" not in result
        assert "userNonVisibleData" not in result
        assert "personalNumber" not in result
        assert "callbackUrl" not in result
        assert "webhookUrl" not in result
        assert "state" not in result


# ---------------------------------------------------------------------------
# AuthSession.from_api
# ---------------------------------------------------------------------------


class TestAuthSession:
    def test_from_api(self):
        data = {
            "sessionId": "sess-001",
            "provider": "bankid",
            "orderRef": "order-ref-abc",
            "autoStartToken": "auto-token-123",
            "qrStartToken": "qr-token-456",
            "qrStartSecret": "qr-secret-789",
            "subscriptionToken": "sub-token-xyz",
            "sessionExpiresAt": "2026-06-15T12:05:00Z",
        }
        session = AuthSession.from_api(data)
        assert session.session_id == "sess-001"
        assert session.provider == "bankid"
        assert session.order_ref == "order-ref-abc"
        assert session.auto_start_token == "auto-token-123"
        assert session.qr_start_token == "qr-token-456"
        assert session.qr_start_secret == "qr-secret-789"
        assert session.subscription_token == "sub-token-xyz"
        assert isinstance(session.session_expires_at, datetime)


# ---------------------------------------------------------------------------
# User.from_api
# ---------------------------------------------------------------------------


class TestUser:
    def test_from_api_with_name(self):
        data = {
            "personalNumber": "199001011234",
            "givenName": "Anna",
            "surname": "Svensson",
            "name": "Anna Svensson",
        }
        user = User.from_api(data)
        assert user.personal_number == "199001011234"
        assert user.given_name == "Anna"
        assert user.surname == "Svensson"
        assert user.name == "Anna Svensson"

    def test_from_api_without_name(self):
        data = {
            "personalNumber": "199505051234",
            "givenName": "Erik",
            "surname": "Johansson",
        }
        user = User.from_api(data)
        assert user.name is None
        assert user.given_name == "Erik"


# ---------------------------------------------------------------------------
# Signature.from_api
# ---------------------------------------------------------------------------


class TestSignature:
    def test_from_api_full(self):
        data = {
            "value": "base64-sig-value",
            "ocspResponse": "base64-ocsp",
            "signedData": "base64-signed",
        }
        sig = Signature.from_api(data)
        assert sig.value == "base64-sig-value"
        assert sig.ocsp_response == "base64-ocsp"
        assert sig.signed_data == "base64-signed"

    def test_from_api_without_signed_data(self):
        data = {"value": "sig", "ocspResponse": "ocsp"}
        sig = Signature.from_api(data)
        assert sig.signed_data is None


# ---------------------------------------------------------------------------
# CollectResult.from_api
# ---------------------------------------------------------------------------


class TestCollectResult:
    def test_from_api_pending(self):
        data = {
            "sessionId": "sess-001",
            "status": "pending",
        }
        result = CollectResult.from_api(data)
        assert result.session_id == "sess-001"
        assert result.status == "pending"
        assert result.user is None
        assert result.signature is None
        assert result.token is None
        assert result.completed_at is None

    def test_from_api_completed(self):
        data = {
            "sessionId": "sess-002",
            "status": "complete",
            "token": "jwt-token-xyz",
            "user": {
                "personalNumber": "199001011234",
                "givenName": "Anna",
                "surname": "Svensson",
                "name": "Anna Svensson",
            },
            "signature": {
                "value": "sig-value",
                "ocspResponse": "ocsp-resp",
                "signedData": "signed-data",
            },
            "completedAt": "2026-06-15T12:01:00Z",
        }
        result = CollectResult.from_api(data)
        assert result.status == "complete"
        assert result.token == "jwt-token-xyz"
        assert result.user is not None
        assert result.user.given_name == "Anna"
        assert result.signature is not None
        assert result.signature.value == "sig-value"
        assert result.completed_at is not None

    def test_from_api_with_null_user_and_signature(self):
        data = {
            "sessionId": "sess-003",
            "status": "pending",
            "user": None,
            "signature": None,
        }
        result = CollectResult.from_api(data)
        assert result.user is None
        assert result.signature is None


# ---------------------------------------------------------------------------
# SessionStatus.from_api
# ---------------------------------------------------------------------------


class TestSessionStatus:
    def test_from_api_minimal(self):
        data = {"sessionId": "sess-001", "status": "pending"}
        st = SessionStatus.from_api(data)
        assert st.session_id == "sess-001"
        assert st.status == "pending"
        assert st.hint_code is None
        assert st.message is None
        assert st.order_count is None
        assert st.max_orders is None
        assert st.session_expires_in_seconds is None

    def test_from_api_full(self):
        data = {
            "sessionId": "sess-004",
            "status": "pending",
            "hintCode": "outstandingTransaction",
            "message": "Waiting for user",
            "orderCount": 2,
            "maxOrders": 5,
            "sessionExpiresInSeconds": 120,
        }
        st = SessionStatus.from_api(data)
        assert st.hint_code == "outstandingTransaction"
        assert st.message == "Waiting for user"
        assert st.order_count == 2
        assert st.max_orders == 5
        assert st.session_expires_in_seconds == 120


# ---------------------------------------------------------------------------
# QRCodeResult.from_api
# ---------------------------------------------------------------------------


class TestQRCodeResult:
    def test_from_api(self):
        data = {"qrData": "bankid.xxxx.yyyy.zzzz", "validForSeconds": 30}
        qr = QRCodeResult.from_api(data)
        assert qr.qr_data == "bankid.xxxx.yyyy.zzzz"
        assert qr.valid_for_seconds == 30


# ---------------------------------------------------------------------------
# ExtendResult.from_api
# ---------------------------------------------------------------------------


class TestExtendResult:
    def test_from_api_success(self):
        data = {
            "extended": True,
            "newExpiresAt": "2026-06-15T12:10:00Z",
            "sessionExpiresInSeconds": 586,
        }
        ext = ExtendResult.from_api(data)
        assert ext.extended is True
        assert ext.error is None
        assert ext.new_expires_at is not None
        assert ext.session_expires_in_seconds == 586

    def test_from_api_failure(self):
        data = {"extended": False, "error": "Session cannot be extended"}
        ext = ExtendResult.from_api(data)
        assert ext.extended is False
        assert ext.error == "Session cannot be extended"
        assert ext.new_expires_at is None


# ---------------------------------------------------------------------------
# UsageStats.from_api
# ---------------------------------------------------------------------------


class TestUsageStats:
    def test_from_api(self):
        data = {
            "year": 2025,
            "month": 6,
            "provider": "bankid",
            "authenticationsStarted": 150,
            "authenticationsCompleted": 120,
            "authenticationsFailed": 30,
        }
        usage = UsageStats.from_api(data)
        assert usage.year == 2025
        assert usage.month == 6
        assert usage.provider == "bankid"
        assert usage.authentications_started == 150
        assert usage.authentications_completed == 120
        assert usage.authentications_failed == 30


# ---------------------------------------------------------------------------
# IpInfo.from_api
# ---------------------------------------------------------------------------


class TestIpInfo:
    def test_from_api_full(self):
        data = {
            "ipAddress": "203.0.113.42",
            "countryCode": "SE",
            "isTor": False,
            "isLikelyVpn": True,
        }
        ip = IpInfo.from_api(data)
        assert ip.ip_address == "203.0.113.42"
        assert ip.country_code == "SE"
        assert ip.is_tor is False
        assert ip.is_likely_vpn is True

    def test_from_api_defaults(self):
        data = {"ipAddress": "10.0.0.1"}
        ip = IpInfo.from_api(data)
        assert ip.country_code is None
        assert ip.is_tor is False
        assert ip.is_likely_vpn is False


# ---------------------------------------------------------------------------
# RiskAssessment.from_api
# ---------------------------------------------------------------------------


class TestRiskAssessment:
    def test_from_api(self):
        data = {"level": "low", "score": 15}
        risk = RiskAssessment.from_api(data)
        assert risk.level == "low"
        assert risk.score == 15


# ---------------------------------------------------------------------------
# WebhookPayload
# ---------------------------------------------------------------------------


class TestWebhookPayload:
    def test_construction(self):
        payload = WebhookPayload(
            event="auth.completed",
            timestamp=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
            data={"sessionId": "sess-001", "user": {"givenName": "Anna"}},
        )
        assert payload.event == "auth.completed"
        assert payload.data["sessionId"] == "sess-001"


# ---------------------------------------------------------------------------
# IpIntelligence.from_api
# ---------------------------------------------------------------------------


class TestIpIntelligence:
    def test_from_api_full(self):
        data = {
            "initiatingIp": {
                "ipAddress": "1.2.3.4",
                "countryCode": "SE",
                "isTor": False,
                "isLikelyVpn": False,
            },
            "deviceIp": {
                "ipAddress": "5.6.7.8",
                "countryCode": "SE",
                "isTor": False,
                "isLikelyVpn": False,
            },
            "overallRisk": {"level": "low", "score": 10, "indicators": []},
        }
        intel = IpIntelligence.from_api(data)
        assert intel.initiating_ip is not None
        assert intel.initiating_ip.ip_address == "1.2.3.4"
        assert intel.device_ip is not None
        assert intel.device_ip.ip_address == "5.6.7.8"
        assert intel.overall_risk is not None
        assert intel.overall_risk.level == "low"
        assert intel.overall_risk.score == 10

    def test_from_api_none_fields(self):
        intel = IpIntelligence.from_api({})
        assert intel.initiating_ip is None
        assert intel.overall_risk is None


# ---------------------------------------------------------------------------
# AuthCompletedData with ip_intelligence
# ---------------------------------------------------------------------------


class TestAuthCompletedData:
    def test_from_api_without_ip_intelligence(self):
        data = {
            "sessionId": "sess-001",
            "status": "complete",
            "provider": "bankid",
            "user": {
                "personalNumber": "199001011234",
                "givenName": "Anna",
                "surname": "Svensson",
            },
            "state": "my-state",
        }
        result = AuthCompletedData.from_api(data)
        assert result.session_id == "sess-001"
        assert result.user.given_name == "Anna"
        assert result.ip_intelligence is None

    def test_from_api_with_ip_intelligence(self):
        data = {
            "sessionId": "sess-002",
            "status": "complete",
            "provider": "bankid",
            "user": {
                "personalNumber": "199001011234",
                "givenName": "Anna",
                "surname": "Svensson",
            },
            "ipIntelligence": {
                "initiatingIp": {"ipAddress": "203.0.113.42", "countryCode": "SE"},
                "overallRisk": {"level": "low", "score": 5, "indicators": []},
            },
        }
        result = AuthCompletedData.from_api(data)
        assert result.ip_intelligence is not None
        assert result.ip_intelligence.initiating_ip.ip_address == "203.0.113.42"
        assert result.ip_intelligence.overall_risk.level == "low"


# ---------------------------------------------------------------------------
# SignCompletedData with ip_intelligence
# ---------------------------------------------------------------------------


class TestSignCompletedData:
    def test_from_api_without_ip_intelligence(self):
        data = {
            "sessionId": "sess-001",
            "status": "complete",
            "provider": "bankid",
            "user": {
                "personalNumber": "199001011234",
                "givenName": "Anna",
                "surname": "Svensson",
            },
            "signature": {"value": "sig-val", "ocspResponse": "ocsp-val"},
        }
        result = SignCompletedData.from_api(data)
        assert result.signature.value == "sig-val"
        assert result.ip_intelligence is None

    def test_from_api_with_ip_intelligence(self):
        data = {
            "sessionId": "sess-002",
            "status": "complete",
            "provider": "bankid",
            "user": {
                "personalNumber": "199001011234",
                "givenName": "Anna",
                "surname": "Svensson",
            },
            "signature": {"value": "sig-val", "ocspResponse": "ocsp-val"},
            "ipIntelligence": {
                "initiatingIp": {"ipAddress": "10.0.0.1"},
                "overallRisk": {"level": "high", "score": 85, "indicators": []},
            },
        }
        result = SignCompletedData.from_api(data)
        assert result.ip_intelligence is not None
        assert result.ip_intelligence.overall_risk.score == 85


# ---------------------------------------------------------------------------
# EnrichmentCompletedData
# ---------------------------------------------------------------------------


class TestEnrichmentCompletedData:
    def test_from_api_full(self):
        data = {
            "enrichmentId": "enr-001",
            "sessionId": "sess-001",
            "status": "completed",
            "secureUrl": "https://id.tic.io/enrichment/data/token-abc",
            "secureUrlExpiresAtUtc": "2026-06-15T12:30:00Z",
            "state": "my-state",
        }
        result = EnrichmentCompletedData.from_api(data)
        assert result.enrichment_id == "enr-001"
        assert result.session_id == "sess-001"
        assert result.secure_url == "https://id.tic.io/enrichment/data/token-abc"
        assert result.state == "my-state"
        assert result.secure_url_expires_at_utc is not None

    def test_from_api_minimal(self):
        data = {
            "enrichmentId": "enr-002",
            "sessionId": "sess-002",
            "status": "completed",
            "secureUrl": "https://example.com/data",
        }
        result = EnrichmentCompletedData.from_api(data)
        assert result.state is None
        assert result.secure_url_expires_at_utc is None


# ---------------------------------------------------------------------------
# EnrichmentFailedData
# ---------------------------------------------------------------------------


class TestEnrichmentFailedData:
    def test_from_api_full(self):
        data = {
            "enrichmentId": "enr-003",
            "sessionId": "sess-003",
            "status": "failed",
            "error": "Session too old",
            "state": "my-state",
        }
        result = EnrichmentFailedData.from_api(data)
        assert result.enrichment_id == "enr-003"
        assert result.error == "Session too old"
        assert result.state == "my-state"

    def test_from_api_minimal(self):
        data = {
            "enrichmentId": "enr-004",
            "sessionId": "sess-004",
            "status": "failed",
        }
        result = EnrichmentFailedData.from_api(data)
        assert result.error is None
        assert result.state is None
