# TIC Identity Python

Unofficial Python client for [TIC Identity](https://id.tic.io) - Swedish BankID authentication and digital signing. Not affiliated with or endorsed by TIC Identity.

Async-first, built on `httpx`, `websockets`, and `pydantic`.

## Installation

```bash
pip install tic-identity-python
```

Requires Python 3.11+.

## Quick Start - Authentication

```python
import asyncio
from tic import TicClient, TicHub

async def authenticate(user_ip: str):
    async with TicClient(api_key="your-api-key") as client:
        # 1. Start a BankID auth session
        session = await client.start_auth(user_ip)
        print(f"Session: {session.session_id}")
        print(f"Auto-start token: {session.auto_start_token}")

        # 2. Connect to the real-time hub
        hub = TicHub()
        await hub.connect()

        # 3. Register event handlers
        hub.on_status_changed(lambda s: print(f"Status: {s.status} ({s.hint_code})"))
        hub.on_completed(lambda c: print(f"Authenticated: {c.user.name} ({c.user.personal_number})"))
        hub.on_failed(lambda f: print(f"Failed: {f.hint_code} - {f.message}"))

        # 4. Subscribe to session updates
        await hub.subscribe(session.session_id, session.subscription_token)

        # 5. Optionally poll QR codes for desktop flows
        qr = await client.get_qr(session.session_id)
        print(f"QR data: {qr.qr_data}")

        # Keep listening until completed/failed
        await asyncio.sleep(60)
        await hub.disconnect()

asyncio.run(authenticate("192.168.1.1"))
```

## Digital Signing

```python
async def sign_document(user_ip: str):
    async with TicClient(api_key="your-api-key") as client:
        session = await client.start_sign(
            user_ip,
            user_visible_data="I agree to the terms of service.",
            user_visible_data_format="simpleMarkdownV1",  # optional
            user_non_visible_data="contract-id:abc123",   # optional
        )

        # Use the hub for real-time updates (same as auth)
        hub = TicHub()
        await hub.connect()
        hub.on_completed(lambda c: print(f"Signed by {c.user.name}"))
        await hub.subscribe(session.session_id, session.subscription_token)

        # Or poll via REST
        result = await client.collect(session.session_id)
        if result.status == "complete":
            print(f"Signature: {result.signature.value}")
            print(f"OCSP response: {result.signature.ocsp_response}")
```

## Webhook Verification

When using `webhook_url` in `start_auth` or `start_sign`, verify incoming webhooks with your webhook secret:

```python
from tic import verify_signature, TicWebhookError

def handle_webhook(request):
    try:
        payload = verify_signature(
            payload=request.body,
            timestamp=request.headers["X-Ormeo-Timestamp"],
            signature=request.headers["X-Ormeo-Signature"],
            secret="your-webhook-secret",
            max_age_seconds=300,  # default
        )
        print(f"Event: {payload.event}")
        print(f"Data: {payload.data}")
    except TicWebhookError as e:
        print(f"Verification failed: {e}")
```

The `verify_signature` function checks the HMAC-SHA256 signature, rejects stale timestamps, and returns a parsed `WebhookPayload`.

## Typed Webhook Parsing

After verifying a webhook, use `parse_webhook_data()` to get a typed model instead of a raw dict:

```python
from tic import verify_signature, parse_webhook_data, AuthCompletedData, SignCompletedData

payload = verify_signature(payload=body, timestamp=ts, signature=sig, secret=secret)
data = parse_webhook_data(payload)

if isinstance(data, AuthCompletedData):
    print(f"Auth completed: {data.user.name} ({data.user.personal_number})")
elif isinstance(data, SignCompletedData):
    print(f"Signed by: {data.user.name}")
    print(f"Signature: {data.signature.value}")
```

Returns `AuthCompletedData` for `auth.completed`, `SignCompletedData` for `sign.completed`, or the raw `dict` for unknown events.

## Enrichment API

Request enrichment data (SPAR, company roles, property ownership, income, IP intelligence) after a completed session:

```python
from tic import TicClient, EnrichmentType, EnrichmentStatus

async with TicClient(api_key="your-api-key") as client:
    # 1. Start enrichment after a completed auth session
    enrichment = await client.start_enrichment(
        session_id="your-session-id",
        types=[EnrichmentType.SPAR, EnrichmentType.COMPANY_ROLES],
        webhook_url="https://example.com/webhook",  # optional
    )
    print(f"Enrichment ID: {enrichment.enrichment_id}")
    print(f"Status: {enrichment.status}")

    # 2. Check status (or wait for webhook)
    status = await client.get_enrichment_status(enrichment.enrichment_id)
    if status.status == EnrichmentStatus.COMPLETED:
        # 3. Retrieve the data via the secure URL token
        data = await client.get_enrichment_data(token=status.secure_url.split("/")[-1])
        if data.spar:
            print(f"Name: {data.spar.Namn_Fornamn} {data.spar.Namn_Efternamn}")
        if data.company_roles:
            for role in data.company_roles:
                print(f"  {role.legal_name} - {role.position_descriptions}")

    # 4. List available enrichment types for your tenant
    types = await client.get_enrichment_types()
    for t in types:
        print(f"{t.type}: {t.description} (enabled={t.enabled})")
```

Available enrichment types: `SPAR`, `CompanyRoles`, `PropertyOwnership`, `Income`, `IpIntelligence`, `Full`.

## Data Verification API

Look up Swedish companies, credit scores, and signing authority without requiring a BankID session:

```python
from tic import TicClient

async with TicClient(api_key="your-api-key") as client:
    # Company lookup by country code + registration number
    company = await client.get_company("SE", "5566112233")
    print(f"{company.data.company_name} ({company.data.activity_status})")
    print(f"VAT registered: {company.data.is_registered_for_vat}")
    print(f"Representatives: {len(company.data.representatives or [])}")

    # Credit score
    credit = await client.get_credit("SE", "5566112233")
    print(f"Credit score: {credit.data.credit_score}/100")
    print(f"Risk forecast: {credit.data.risk_forecast}%")

    # Signing authority analysis (AI-generated)
    authority = await client.get_signing_authority("SE", "5566112233")
    print(f"Summary: {authority.data.analysis.summary}")
    for person in authority.data.analysis.eligible_persons:
        print(f"  {person.name} - can sign alone: {person.can_sign_alone}")
```

All three endpoints also have `_by_id` variants that accept an internal `company_id`:

```python
company = await client.get_company_by_id("12345")
credit  = await client.get_credit_by_id("12345")
authority = await client.get_signing_authority_by_id("12345")
```

## QR Code Generation

Generate BankID animated QR data locally, without polling the server:

```python
import time
from tic import TicClient, generate_qr_data

async with TicClient(api_key="your-api-key") as client:
    session = await client.start_auth(user_ip)

    # Generate QR data client-side using tokens from the session
    start = time.monotonic()
    while True:
        elapsed = int(time.monotonic() - start)
        qr = generate_qr_data(
            qr_start_token=session.qr_start_token,
            qr_start_secret=session.qr_start_secret,
            elapsed_seconds=elapsed,
        )
        render_qr_image(qr)  # your QR rendering code
        time.sleep(1)
```

The returned string has the format `bankid.<token>.<elapsed>.<hmac>` and should be refreshed every second.

## BankID Helpers

Utility functions for building BankID URLs and parsing callbacks:

```python
from tic import bankid_autostart_url, hosted_login_url, parse_callback

# Desktop BankID autostart (bankid:/// scheme)
url = bankid_autostart_url(
    auto_start_token=session.auto_start_token,
    redirect_url="https://example.com/callback",
)
# -> bankid:///?autostarttoken=...&redirect=...

# Mobile BankID autostart (https://app.bankid.com/)
mobile_url = bankid_autostart_url(
    auto_start_token=session.auto_start_token,
    redirect_url="https://example.com/callback",
    mobile=True,
)

# Hosted-mode login redirect
login_url = hosted_login_url(
    base_url="https://id.tic.io",
    tenant="my-tenant",
    callback="https://example.com/callback",
    state="my-state",
    lang="sv",
)

# Parse callback URL after authentication
result = parse_callback("https://example.com/callback?session_id=abc&token=xyz&state=my-state")
print(result)  # {"session_id": "abc", "token": "xyz", "state": "my-state"}
```

## Messages Endpoint

Retrieve localized BankID status messages:

```python
from tic import TicClient

async with TicClient(api_key="your-api-key") as client:
    messages = await client.get_messages(language="sv")
    for msg in messages:
        print(f"{msg.hint_code}: {msg.message}")
    # outstandingTransaction: Starta BankID-appen...
```

## Constants and Enums

Typed enums for hint codes, session statuses, error codes, webhook events, and headers:

```python
from tic import HintCode, ErrorCode, SessionStatusEnum, WebhookEvent, WebhookHeader, Environment

# BankID hint codes with semantic helpers
if hint == HintCode.USER_SIGN:
    print("User is entering security code")
print(HintCode.EXPIRED_TRANSACTION.is_failed)   # True
print(HintCode.STARTED.is_pending)               # True

# Session status
if status == SessionStatusEnum.COMPLETE:
    collect_result()

# API error codes
try:
    await client.start_auth(ip)
except TicAPIError as e:
    if e.code == ErrorCode.LIMIT_EXCEEDED:
        print("Monthly limit reached")

# Webhook events
if payload.event == WebhookEvent.ENRICHMENT_COMPLETED:
    fetch_enrichment_data()

# Webhook header names
sig = headers[WebhookHeader.SIGNATURE]   # "X-Ormeo-Signature"
ts  = headers[WebhookHeader.TIMESTAMP]   # "X-Ormeo-Timestamp"

# Environment base URLs
client = TicClient(api_key="key", base_url=Environment.PRODUCTION)
```

## REST Client Methods

`TicClient` is an async context manager. All methods are coroutines.

| Method | Description |
|---|---|
| `start_auth(end_user_ip, *, provider, personal_number, callback_url, webhook_url, state)` | Start a BankID auth session. Returns `AuthSession`. |
| `start_sign(end_user_ip, user_visible_data, *, provider, user_visible_data_format, user_non_visible_data, personal_number, callback_url, webhook_url, state)` | Start a BankID signing session. Returns `AuthSession`. |
| `collect(session_id)` | Collect the final result (user, signature, token). Returns `CollectResult`. |
| `get_status(session_id)` | Get current session status. Returns `SessionStatus`. |
| `poll(session_id)` | Long-poll for status change. Returns `SessionStatus`. |
| `get_qr(session_id)` | Get animated QR code data. Returns `QRCodeResult`. |
| `cancel(session_id)` | Cancel a session. Returns `bool`. |
| `extend(session_id)` | Extend session timeout. Returns `ExtendResult`. |
| `get_usage(year, month)` | Get monthly usage stats. Returns `UsageStats`. |
| `get_messages(language)` | Get localized BankID messages. Returns `list[LocalizedMessage]`. |
| `start_enrichment(session_id, types, *, webhook_url, state)` | Start enrichment for a completed session. Returns `EnrichmentResponse`. |
| `get_enrichment_status(enrichment_id)` | Check enrichment progress. Returns `EnrichmentResponse`. |
| `get_enrichment_types()` | List available enrichment types. Returns `list[EnrichmentTypeInfo]`. |
| `get_enrichment_data(token)` | Retrieve enrichment data. Returns `EnrichmentData`. |
| `get_company(country_code, reg_nr)` | Look up company info. Returns `CompanyLookupResponse`. |
| `get_company_by_id(company_id)` | Look up company by internal ID. Returns `CompanyLookupResponse`. |
| `get_credit(country_code, reg_nr)` | Get company credit score. Returns `CompanyCreditResponse`. |
| `get_credit_by_id(company_id)` | Get credit by internal ID. Returns `CompanyCreditResponse`. |
| `get_signing_authority(country_code, reg_nr)` | Analyse signing authority. Returns `SigningAuthorityResponse`. |
| `get_signing_authority_by_id(company_id)` | Signing authority by internal ID. Returns `SigningAuthorityResponse`. |

You can also inject your own `httpx.AsyncClient`:

```python
client = TicClient(api_key="key", http_client=my_httpx_client)
```

## SignalR Hub Events

`TicHub` connects to the real-time SignalR hub over WebSocket. After calling `hub.connect()` and `hub.subscribe(session_id, subscription_token)`, the following events fire:

| Helper | Event | Payload |
|---|---|---|
| `on_qr_code(handler)` | `OnQRCode` | `str` - animated QR code data |
| `on_status_changed(handler)` | `OnStatusChanged` | `StatusChanged(status, hint_code, message, message_en)` |
| `on_completed(handler)` | `OnCompleted` | `Completed(session_id, status, user, completed_at)` |
| `on_failed(handler)` | `OnFailed` | `Failed(hint_code, message, message_en)` |
| `on_cancelled(handler)` | `OnCancelled` | No arguments |
| `on_timeout_warning(handler)` | `OnTimeoutWarning` | `TimeoutWarning(seconds_remaining, can_extend)` |
| `on_order_regenerated(handler)` | `OnOrderRegenerated` | `OrderRegenerated(order_count, max_orders, session_expires_in_seconds)` |

## Typed Hub Responses

Hub invocable methods return typed pydantic models:

```python
hub = TicHub()
await hub.connect()

# subscribe() returns SubscribeResponse
sub = await hub.subscribe(session_id, subscription_token)
print(f"Provider: {sub.provider}, Status: {sub.status}")
print(f"Expires: {sub.session_expires_at}")

# get_status() returns AuthStatusResponse
status = await hub.get_status()
if status:
    print(f"{status.status} / {status.hint_code}")
    print(f"Orders: {status.order_count}/{status.max_orders}")

# extend_session() returns ExtendResult
ext = await hub.extend_session()
print(f"Extended: {ext.success}, new expiry: {ext.new_expires_at}")
```

| Method | Description | Return type |
|---|---|---|
| `subscribe(session_id, subscription_token)` | Subscribe to a session's events | `SubscribeResponse` |
| `cancel_session()` | Cancel the active session | `None` |
| `get_qr_code()` | Request current QR code data | `str \| None` |
| `get_status()` | Request current status | `AuthStatusResponse \| None` |
| `extend_session()` | Extend session timeout | `ExtendResult` |

Handlers can be sync or async - async handlers are automatically scheduled as tasks.

## Exceptions

| Exception | When |
|---|---|
| `TicAPIError` | HTTP error from the REST API. Has `status_code`, `code`, `message`, `details`. |
| `TicHubError` | SignalR hub connection or invocation error. |
| `TicWebhookError` | Webhook signature verification failure. |
| `TicError` | Base class for all of the above. |

## License

MIT
