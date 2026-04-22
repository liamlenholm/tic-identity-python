from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from .data import (
    CompanyCreditResponse,
    CompanyLookupResponse,
    SigningAuthorityResponse,
)
from .enrichment import (
    EnrichmentData,
    EnrichmentResponse,
    EnrichmentTypeInfo,
    EnrichmentTypesResponse,
)
from .exceptions import TicAPIError
from .models import (
    AuthSession,
    AuthStartRequest,
    CollectResult,
    ExtendResult,
    MessagesResponse,
    QRCodeResult,
    SessionStatus,
    SignStartRequest,
    UsageStats,
)


@dataclass
class RateLimitInfo:
    """Rate limit state parsed from API response headers."""

    limit_minute: int | None = None
    remaining_minute: int | None = None
    limit_hour: int | None = None
    remaining_hour: int | None = None
    limit_day: int | None = None
    remaining_day: int | None = None
    retry_after: int | None = None
    login_limit: int | None = None
    login_remaining: int | None = None


DEFAULT_BASE_URL = "https://id.tic.io"


class TicClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._max_retries = max_retries
        self._rate_limit = RateLimitInfo()
        self._client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    @property
    def rate_limit(self) -> RateLimitInfo:
        return self._rate_limit

    async def __aenter__(self) -> TicClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _parse_rate_limit(headers: httpx.Headers) -> RateLimitInfo:
        def _int(key: str) -> int | None:
            val = headers.get(key)
            return int(val) if val is not None else None

        return RateLimitInfo(
            limit_minute=_int("X-RateLimit-Limit-Minute"),
            remaining_minute=_int("X-RateLimit-Remaining-Minute"),
            limit_hour=_int("X-RateLimit-Limit-Hour"),
            remaining_hour=_int("X-RateLimit-Remaining-Hour"),
            limit_day=_int("X-RateLimit-Limit-Day"),
            remaining_day=_int("X-RateLimit-Remaining-Day"),
            retry_after=_int("Retry-After"),
            login_limit=_int("X-Login-RateLimit-Limit"),
            login_remaining=_int("X-Login-RateLimit-Remaining"),
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        for attempt in range(self._max_retries + 1):
            resp = await self._client.request(method, path, **kwargs)
            self._rate_limit = self._parse_rate_limit(resp.headers)

            if resp.status_code == 429 and attempt < self._max_retries:
                retry_after = self._rate_limit.retry_after or (2**attempt)
                await asyncio.sleep(retry_after)
                continue

            if resp.status_code >= 400:
                try:
                    body = resp.json()
                except ValueError:
                    raise TicAPIError(resp.status_code, "unknown", resp.text)
                err = body.get("error", {})
                if isinstance(err, dict):
                    raise TicAPIError(
                        status_code=resp.status_code,
                        code=err.get("code", "unknown"),
                        message=err.get("message", resp.text),
                        details=err.get("details"),
                    )
                raise TicAPIError(
                    status_code=resp.status_code,
                    code=str(err) if err else "unknown",
                    message=body.get("message", resp.text),
                )
            return resp.json()

    # --- Authentication ---

    async def start_auth(
        self,
        end_user_ip: str,
        *,
        provider: str = "bankid",
        user_agent: str | None = None,
        personal_number: str | None = None,
        callback_url: str | None = None,
        webhook_url: str | None = None,
        state: str | None = None,
    ) -> AuthSession:
        req = AuthStartRequest(
            end_user_ip=end_user_ip,
            user_agent=user_agent,
            personal_number=personal_number,
            callback_url=callback_url,
            webhook_url=webhook_url,
            state=state,
        )
        data = await self._request(
            "POST", f"/api/v1/auth/{provider}/start", json=req.to_api()
        )
        return AuthSession.from_api(data)

    async def collect(self, session_id: str) -> CollectResult:
        data = await self._request("GET", f"/api/v1/auth/{session_id}/collect")
        return CollectResult.from_api(data)

    async def get_status(self, session_id: str) -> SessionStatus:
        data = await self._request("GET", f"/api/v1/auth/{session_id}/status")
        return SessionStatus.from_api(data)

    async def poll(self, session_id: str) -> SessionStatus:
        data = await self._request("POST", f"/api/v1/auth/{session_id}/poll")
        return SessionStatus.from_api(data)

    async def get_qr(self, session_id: str) -> QRCodeResult:
        data = await self._request("GET", f"/api/v1/auth/{session_id}/qr")
        return QRCodeResult.from_api(data)

    async def cancel(self, session_id: str) -> bool:
        data = await self._request("DELETE", f"/api/v1/auth/{session_id}")
        return data.get("cancelled", False)

    async def extend(self, session_id: str) -> ExtendResult:
        data = await self._request("POST", f"/api/v1/auth/{session_id}/extend")
        return ExtendResult.from_api(data)

    # --- Digital Signing ---

    async def start_sign(
        self,
        end_user_ip: str,
        user_visible_data: str,
        *,
        provider: str = "bankid",
        user_agent: str | None = None,
        user_visible_data_format: str | None = None,
        user_non_visible_data: str | None = None,
        personal_number: str | None = None,
        callback_url: str | None = None,
        webhook_url: str | None = None,
        state: str | None = None,
    ) -> AuthSession:
        req = SignStartRequest(
            end_user_ip=end_user_ip,
            user_agent=user_agent,
            user_visible_data=user_visible_data,
            user_visible_data_format=user_visible_data_format,
            user_non_visible_data=user_non_visible_data,
            personal_number=personal_number,
            callback_url=callback_url,
            webhook_url=webhook_url,
            state=state,
        )
        data = await self._request(
            "POST", f"/api/v1/auth/{provider}/sign", json=req.to_api()
        )
        return AuthSession.from_api(data)

    # --- Usage ---

    async def get_usage(self, year: int, month: int) -> UsageStats:
        data = await self._request(
            "GET", "/api/v1/usage", params={"year": year, "month": month}
        )
        return UsageStats.from_api(data)

    # --- Messages ---

    async def get_messages(self, language: str = "sv") -> MessagesResponse:
        data = await self._request(
            "GET", "/api/v1/messages", params={"language": language}
        )
        return MessagesResponse.from_api(data)

    # --- Enrichment ---

    async def start_enrichment(
        self,
        session_id: str,
        types: list[str],
        *,
        webhook_url: str | None = None,
        state: str | None = None,
    ) -> EnrichmentResponse:
        body: dict[str, Any] = {"sessionId": session_id, "types": types}
        if webhook_url is not None:
            body["webhookUrl"] = webhook_url
        if state is not None:
            body["state"] = state
        data = await self._request("POST", "/api/v1/enrichment", json=body)
        return EnrichmentResponse.from_api(data)

    async def get_enrichment_status(self, enrichment_id: str) -> EnrichmentResponse:
        data = await self._request("GET", f"/api/v1/enrichment/{enrichment_id}/status")
        return EnrichmentResponse.from_api(data)

    async def get_enrichment_types(self) -> EnrichmentTypesResponse:
        data = await self._request("GET", "/api/v1/enrichment/types")
        return EnrichmentTypesResponse.from_api(data)

    async def get_enrichment_data(self, token: str) -> EnrichmentData:
        data = await self._request("GET", f"/api/v1/enrichment/data/{token}")
        return EnrichmentData.from_api(data)

    # --- Data Verification ---

    async def get_company(
        self, country_code: str, reg_nr: str
    ) -> CompanyLookupResponse:
        data = await self._request(
            "GET", f"/api/v1/data/company/{country_code}/{reg_nr}"
        )
        return CompanyLookupResponse.from_api(data)

    async def get_company_by_id(self, company_id: str) -> CompanyLookupResponse:
        data = await self._request("GET", f"/api/v1/data/company/id/{company_id}")
        return CompanyLookupResponse.from_api(data)

    async def get_credit(self, country_code: str, reg_nr: str) -> CompanyCreditResponse:
        data = await self._request(
            "GET", f"/api/v1/data/credit/{country_code}/{reg_nr}"
        )
        return CompanyCreditResponse.from_api(data)

    async def get_credit_by_id(self, company_id: str) -> CompanyCreditResponse:
        data = await self._request("GET", f"/api/v1/data/credit/id/{company_id}")
        return CompanyCreditResponse.from_api(data)

    async def get_signing_authority(
        self, country_code: str, reg_nr: str
    ) -> SigningAuthorityResponse:
        data = await self._request(
            "GET",
            f"/api/v1/data/company/{country_code}/{reg_nr}/signing-authority-analysis",
        )
        return SigningAuthorityResponse.from_api(data)

    async def get_signing_authority_by_id(
        self, company_id: str
    ) -> SigningAuthorityResponse:
        data = await self._request(
            "GET",
            f"/api/v1/data/company/id/{company_id}/signing-authority-analysis",
        )
        return SigningAuthorityResponse.from_api(data)
