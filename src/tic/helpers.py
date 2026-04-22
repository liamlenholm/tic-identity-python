"""URL builder helpers for TIC Identity integrations.

Convenience functions for constructing BankID autostart URLs, hosted-mode
login redirects, and parsing callback query parameters.

Uses only the Python standard library (urllib.parse).
"""

from __future__ import annotations

from urllib.parse import parse_qs, quote, urlencode, urlparse


def bankid_autostart_url(
    auto_start_token: str,
    redirect_url: str,
    *,
    mobile: bool = False,
) -> str:
    """Build a BankID autostart URL for same-device authentication.

    Parameters
    ----------
    auto_start_token:
        The ``autoStartToken`` from the ``/start`` response.
    redirect_url:
        Where the user should be sent after interacting with the BankID app.
    mobile:
        If *True*, returns an ``https://app.bankid.com/`` URL suitable for
        mobile browsers.  Otherwise returns a ``bankid:///`` URI for desktop.

    Returns
    -------
    str
        A fully-formed BankID launch URL.
    """
    encoded_redirect = quote(redirect_url, safe="")

    if mobile:
        return (
            f"https://app.bankid.com/"
            f"?autostarttoken={auto_start_token}"
            f"&redirect={encoded_redirect}"
        )

    return f"bankid:///?autostarttoken={auto_start_token}&redirect={encoded_redirect}"


def hosted_login_url(
    base_url: str,
    tenant: str,
    callback: str,
    *,
    state: str | None = None,
    provider: str = "bankid",
    pnr: str | None = None,
    lang: str | None = None,
) -> str:
    """Build a TIC Identity hosted-mode login redirect URL.

    Parameters
    ----------
    base_url:
        The TIC Identity base URL (e.g. ``https://id.tic.io``).
    tenant:
        Tenant slug.
    callback:
        The callback URL to redirect the user to after authentication.
    state:
        Optional opaque state value passed through the flow.
    provider:
        Identity provider, defaults to ``"bankid"``.
    pnr:
        Optional pre-filled personal number.
    lang:
        Optional language code (``sv``, ``en``, ``da``, ``no``, ``fi``).

    Returns
    -------
    str
        A hosted login URL ready for redirection.
    """
    base = base_url.rstrip("/")
    params: dict[str, str] = {"callback": callback}

    if state is not None:
        params["state"] = state
    if provider != "bankid":
        params["provider"] = provider
    if pnr is not None:
        params["pnr"] = pnr
    if lang is not None:
        params["lang"] = lang

    return f"{base}/{tenant}/login?{urlencode(params)}"


def parse_callback(url: str) -> dict[str, str]:
    """Extract authentication results from a TIC Identity callback URL.

    Parses the ``session_id``, ``token``, ``state``, and ``signature``
    query parameters that TIC Identity appends to the callback URL after
    a successful authentication.

    Parameters
    ----------
    url:
        The full callback URL (including query string).

    Returns
    -------
    dict[str, str]
        A dictionary with any of the recognised keys that were present:
        ``session_id``, ``token``, ``state``, ``signature``.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=False)

    known_keys = ("session_id", "token", "state", "signature")
    result: dict[str, str] = {}

    for key in known_keys:
        values = qs.get(key)
        if values:
            result[key] = values[0]

    return result
