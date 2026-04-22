"""Tests for tic.client — TicClient REST methods with respx-mocked httpx."""

from __future__ import annotations

import httpx
import pytest
import respx

from tic.client import DEFAULT_BASE_URL, RateLimitInfo, TicClient
from tic.exceptions import TicAPIError
from tic.models import (
    AuthSession,
    CollectResult,
    ExtendResult,
    QRCodeResult,
    SessionStatus,
    UsageStats,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

API_KEY = "test-api-key-000"

AUTH_SESSION_RESPONSE = {
    "sessionId": "sess-100",
    "provider": "bankid",
    "orderRef": "order-ref-100",
    "autoStartToken": "ast-100",
    "qrStartToken": "qrst-100",
    "qrStartSecret": "qrss-100",
    "subscriptionToken": "sub-100",
    "sessionExpiresAt": "2026-06-15T12:05:00Z",
}


@pytest.fixture()
def mock_router():
    with respx.mock(base_url=DEFAULT_BASE_URL) as router:
        yield router


@pytest.fixture()
def client():
    return TicClient(api_key=API_KEY)


# ---------------------------------------------------------------------------
# start_auth
# ---------------------------------------------------------------------------


class TestStartAuth:
    async def test_start_auth_minimal(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/bankid/start").mock(
            return_value=httpx.Response(200, json=AUTH_SESSION_RESPONSE),
        )
        session = await client.start_auth("192.168.1.1")
        assert isinstance(session, AuthSession)
        assert session.session_id == "sess-100"
        assert session.provider == "bankid"

    async def test_start_auth_with_options(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/bankid/start").mock(
            return_value=httpx.Response(200, json=AUTH_SESSION_RESPONSE),
        )
        session = await client.start_auth(
            "10.0.0.1",
            personal_number="199001011234",
            callback_url="https://example.com/cb",
            webhook_url="https://example.com/wh",
            state="my-state",
        )
        assert session.session_id == "sess-100"
        # Verify the request body contained the right fields
        request = mock_router.calls.last.request
        import json

        body = json.loads(request.content)
        assert body["endUserIp"] == "10.0.0.1"
        assert body["personalNumber"] == "199001011234"
        assert body["callbackUrl"] == "https://example.com/cb"
        assert body["webhookUrl"] == "https://example.com/wh"
        assert body["state"] == "my-state"

    async def test_start_auth_custom_provider(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/freja/start").mock(
            return_value=httpx.Response(200, json=AUTH_SESSION_RESPONSE),
        )
        session = await client.start_auth("1.2.3.4", provider="freja")
        assert isinstance(session, AuthSession)


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------


class TestCollect:
    async def test_collect_pending(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.get("/api/v1/auth/sess-100/collect").mock(
            return_value=httpx.Response(
                200,
                json={
                    "sessionId": "sess-100",
                    "status": "pending",
                },
            ),
        )
        result = await client.collect("sess-100")
        assert isinstance(result, CollectResult)
        assert result.status == "pending"
        assert result.user is None

    async def test_collect_completed(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.get("/api/v1/auth/sess-100/collect").mock(
            return_value=httpx.Response(
                200,
                json={
                    "sessionId": "sess-100",
                    "status": "complete",
                    "token": "jwt-abc",
                    "user": {
                        "personalNumber": "199001011234",
                        "givenName": "Anna",
                        "surname": "Svensson",
                        "name": "Anna Svensson",
                    },
                    "signature": {
                        "value": "sig-val",
                        "ocspResponse": "ocsp-val",
                    },
                    "completedAt": "2026-06-15T12:01:00Z",
                },
            ),
        )
        result = await client.collect("sess-100")
        assert result.status == "complete"
        assert result.user is not None
        assert result.user.given_name == "Anna"
        assert result.signature is not None
        assert result.token == "jwt-abc"


# ---------------------------------------------------------------------------
# get_status / poll
# ---------------------------------------------------------------------------


class TestStatus:
    async def test_get_status(self, mock_router: respx.MockRouter, client: TicClient):
        mock_router.get("/api/v1/auth/sess-100/status").mock(
            return_value=httpx.Response(
                200,
                json={
                    "sessionId": "sess-100",
                    "status": "pending",
                    "hintCode": "outstandingTransaction",
                },
            ),
        )
        st = await client.get_status("sess-100")
        assert isinstance(st, SessionStatus)
        assert st.hint_code == "outstandingTransaction"

    async def test_poll(self, mock_router: respx.MockRouter, client: TicClient):
        mock_router.post("/api/v1/auth/sess-100/poll").mock(
            return_value=httpx.Response(
                200,
                json={
                    "sessionId": "sess-100",
                    "status": "pending",
                },
            ),
        )
        st = await client.poll("sess-100")
        assert isinstance(st, SessionStatus)
        assert st.status == "pending"


# ---------------------------------------------------------------------------
# get_qr
# ---------------------------------------------------------------------------


class TestGetQR:
    async def test_get_qr(self, mock_router: respx.MockRouter, client: TicClient):
        mock_router.get("/api/v1/auth/sess-100/qr").mock(
            return_value=httpx.Response(
                200,
                json={
                    "qrData": "bankid.xxxx.yyyy.zzzz",
                    "validForSeconds": 30,
                },
            ),
        )
        qr = await client.get_qr("sess-100")
        assert isinstance(qr, QRCodeResult)
        assert qr.qr_data == "bankid.xxxx.yyyy.zzzz"
        assert qr.valid_for_seconds == 30


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


class TestCancel:
    async def test_cancel_success(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.delete("/api/v1/auth/sess-100").mock(
            return_value=httpx.Response(200, json={"cancelled": True}),
        )
        result = await client.cancel("sess-100")
        assert result is True

    async def test_cancel_returns_false(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.delete("/api/v1/auth/sess-100").mock(
            return_value=httpx.Response(200, json={"cancelled": False}),
        )
        result = await client.cancel("sess-100")
        assert result is False

    async def test_cancel_missing_key(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.delete("/api/v1/auth/sess-100").mock(
            return_value=httpx.Response(200, json={}),
        )
        result = await client.cancel("sess-100")
        assert result is False


# ---------------------------------------------------------------------------
# extend
# ---------------------------------------------------------------------------


class TestExtend:
    async def test_extend_success(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/sess-100/extend").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "newExpiresAt": "2026-06-15T12:10:00Z",
                },
            ),
        )
        ext = await client.extend("sess-100")
        assert isinstance(ext, ExtendResult)
        assert ext.success is True
        assert ext.new_expires_at is not None


# ---------------------------------------------------------------------------
# start_sign
# ---------------------------------------------------------------------------


class TestStartSign:
    async def test_start_sign_minimal(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/bankid/sign").mock(
            return_value=httpx.Response(200, json=AUTH_SESSION_RESPONSE),
        )
        session = await client.start_sign("192.168.1.1", "Sign this document")
        assert isinstance(session, AuthSession)
        assert session.session_id == "sess-100"

    async def test_start_sign_with_all_options(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/bankid/sign").mock(
            return_value=httpx.Response(200, json=AUTH_SESSION_RESPONSE),
        )
        session = await client.start_sign(
            "10.0.0.1",
            "Please sign the contract",
            user_visible_data_format="simpleMarkdownV1",
            user_non_visible_data="hidden-hash",
            personal_number="199001011234",
            callback_url="https://example.com/cb",
            webhook_url="https://example.com/wh",
            state="sign-state-1",
        )
        assert session.session_id == "sess-100"
        import json

        request = mock_router.calls.last.request
        body = json.loads(request.content)
        assert body["userVisibleData"] == "Please sign the contract"
        assert body["userVisibleDataFormat"] == "simpleMarkdownV1"
        assert body["userNonVisibleData"] == "hidden-hash"

    async def test_start_sign_custom_provider(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/freja/sign").mock(
            return_value=httpx.Response(200, json=AUTH_SESSION_RESPONSE),
        )
        session = await client.start_sign("1.2.3.4", "Sign", provider="freja")
        assert isinstance(session, AuthSession)


# ---------------------------------------------------------------------------
# get_usage
# ---------------------------------------------------------------------------


class TestGetUsage:
    async def test_get_usage(self, mock_router: respx.MockRouter, client: TicClient):
        mock_router.get("/api/v1/usage").mock(
            return_value=httpx.Response(
                200,
                json={
                    "year": 2025,
                    "month": 6,
                    "provider": "bankid",
                    "authenticationsStarted": 150,
                    "authenticationsCompleted": 120,
                    "authenticationsFailed": 30,
                },
            ),
        )
        usage = await client.get_usage(2025, 6)
        assert isinstance(usage, UsageStats)
        assert usage.year == 2025
        assert usage.authentications_started == 150


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    async def test_400_error_with_structured_body(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/bankid/start").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": {
                        "code": "invalid_request",
                        "message": "Missing endUserIp",
                        "details": {"field": "endUserIp"},
                    },
                },
            ),
        )
        with pytest.raises(TicAPIError) as exc_info:
            await client.start_auth("bad")
        err = exc_info.value
        assert err.status_code == 400
        assert err.code == "invalid_request"
        assert err.message == "Missing endUserIp"
        assert err.details == {"field": "endUserIp"}

    async def test_401_unauthorized(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/bankid/start").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {"code": "unauthorized", "message": "Invalid API key"},
                },
            ),
        )
        with pytest.raises(TicAPIError) as exc_info:
            await client.start_auth("1.2.3.4")
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "unauthorized"

    async def test_500_error(self, mock_router: respx.MockRouter, client: TicClient):
        mock_router.get("/api/v1/auth/sess-x/collect").mock(
            return_value=httpx.Response(
                500,
                json={
                    "error": {"code": "internal_error", "message": "Something broke"},
                },
            ),
        )
        with pytest.raises(TicAPIError) as exc_info:
            await client.collect("sess-x")
        assert exc_info.value.status_code == 500

    async def test_error_without_json_body(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.get("/api/v1/auth/sess-x/collect").mock(
            return_value=httpx.Response(502, text="Bad Gateway"),
        )
        with pytest.raises(TicAPIError) as exc_info:
            await client.collect("sess-x")
        assert exc_info.value.status_code == 502
        assert exc_info.value.code == "unknown"

    async def test_error_with_empty_error_object(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.get("/api/v1/auth/sess-x/collect").mock(
            return_value=httpx.Response(422, json={"error": {}}),
        )
        with pytest.raises(TicAPIError) as exc_info:
            await client.collect("sess-x")
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "unknown"


# ---------------------------------------------------------------------------
# Context manager / close
# ---------------------------------------------------------------------------


class TestClientLifecycle:
    async def test_async_context_manager(self, mock_router: respx.MockRouter):
        async with TicClient(api_key=API_KEY) as client:
            mock_router.get("/api/v1/auth/sess-1/status").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "sessionId": "sess-1",
                        "status": "pending",
                    },
                ),
            )
            st = await client.get_status("sess-1")
            assert st.status == "pending"

    async def test_close_does_not_close_injected_client(
        self, mock_router: respx.MockRouter
    ):
        external = httpx.AsyncClient(base_url=DEFAULT_BASE_URL)
        client = TicClient(api_key=API_KEY, http_client=external)
        assert client._owns_client is False
        await client.close()
        # External client should still be usable (not closed)
        assert not external.is_closed
        await external.aclose()

    async def test_headers_set(self):
        client = TicClient(api_key="key-123")
        assert client._client.headers["X-Api-Key"] == "key-123"
        assert client._client.headers["Content-Type"] == "application/json"
        await client.close()


# ---------------------------------------------------------------------------
# Rate limit handling
# ---------------------------------------------------------------------------


class TestRateLimiting:
    async def test_rate_limit_headers_parsed(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.get("/api/v1/auth/sess-1/status").mock(
            return_value=httpx.Response(
                200,
                json={"sessionId": "sess-1", "status": "pending"},
                headers={
                    "X-RateLimit-Limit-Minute": "240",
                    "X-RateLimit-Remaining-Minute": "239",
                    "X-RateLimit-Limit-Hour": "3000",
                    "X-RateLimit-Remaining-Hour": "2999",
                },
            ),
        )
        await client.get_status("sess-1")
        rl = client.rate_limit
        assert isinstance(rl, RateLimitInfo)
        assert rl.limit_minute == 240
        assert rl.remaining_minute == 239
        assert rl.limit_hour == 3000
        assert rl.remaining_hour == 2999

    async def test_429_retries_with_retry_after(self, mock_router: respx.MockRouter):
        client = TicClient(api_key=API_KEY, max_retries=2)
        route = mock_router.get("/api/v1/auth/sess-1/status")
        route.side_effect = [
            httpx.Response(
                429, json={"error": "rate_limited"}, headers={"Retry-After": "0"}
            ),
            httpx.Response(200, json={"sessionId": "sess-1", "status": "pending"}),
        ]
        st = await client.get_status("sess-1")
        assert st.status == "pending"
        assert route.call_count == 2
        await client.close()

    async def test_429_exhausts_retries(self, mock_router: respx.MockRouter):
        client = TicClient(api_key=API_KEY, max_retries=1)
        mock_router.get("/api/v1/auth/sess-1/status").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {"code": "rate_limited", "message": "Too many requests"}
                },
                headers={"Retry-After": "0"},
            ),
        )
        with pytest.raises(TicAPIError) as exc_info:
            await client.get_status("sess-1")
        assert exc_info.value.status_code == 429
        await client.close()

    async def test_max_retries_zero_disables_retry(self, mock_router: respx.MockRouter):
        client = TicClient(api_key=API_KEY, max_retries=0)
        mock_router.get("/api/v1/auth/sess-1/status").mock(
            return_value=httpx.Response(
                429,
                json={
                    "error": {"code": "rate_limited", "message": "Too many requests"}
                },
                headers={"Retry-After": "0"},
            ),
        )
        with pytest.raises(TicAPIError) as exc_info:
            await client.get_status("sess-1")
        assert exc_info.value.status_code == 429
        await client.close()

    async def test_login_rate_limit_headers_parsed(
        self, mock_router: respx.MockRouter, client: TicClient
    ):
        mock_router.post("/api/v1/auth/bankid/start").mock(
            return_value=httpx.Response(
                200,
                json=AUTH_SESSION_RESPONSE,
                headers={
                    "X-Login-RateLimit-Limit": "50",
                    "X-Login-RateLimit-Remaining": "48",
                },
            ),
        )
        await client.start_auth("192.168.1.1")
        rl = client.rate_limit
        assert rl.login_limit == 50
        assert rl.login_remaining == 48

    async def test_rate_limit_defaults(self):
        client = TicClient(api_key="key")
        rl = client.rate_limit
        assert rl.limit_minute is None
        assert rl.remaining_minute is None
        assert rl.retry_after is None
        assert rl.login_limit is None
        assert rl.login_remaining is None
        await client.close()
