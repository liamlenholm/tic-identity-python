"""Tests for tic.helpers — URL builders and callback parser."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from tic.helpers import bankid_autostart_url, hosted_login_url, parse_callback


# ---------------------------------------------------------------------------
# bankid_autostart_url
# ---------------------------------------------------------------------------


class TestBankidAutostartUrl:
    TOKEN = "auto-token-abc123"
    REDIRECT = "https://example.com/callback?foo=bar"

    def test_desktop_format(self):
        url = bankid_autostart_url(self.TOKEN, self.REDIRECT)
        assert url.startswith("bankid:///")
        assert f"autostarttoken={self.TOKEN}" in url

    def test_mobile_format(self):
        url = bankid_autostart_url(self.TOKEN, self.REDIRECT, mobile=True)
        assert url.startswith("https://app.bankid.com/")
        assert f"autostarttoken={self.TOKEN}" in url

    def test_desktop_does_not_use_https(self):
        url = bankid_autostart_url(self.TOKEN, self.REDIRECT, mobile=False)
        assert not url.startswith("https://")

    def test_mobile_does_not_use_bankid_scheme(self):
        url = bankid_autostart_url(self.TOKEN, self.REDIRECT, mobile=True)
        assert not url.startswith("bankid://")

    def test_redirect_url_is_encoded(self):
        url = bankid_autostart_url(self.TOKEN, self.REDIRECT)
        # The colon, slashes, question mark, and equals should be percent-encoded
        assert "https%3A%2F%2Fexample.com%2Fcallback%3Ffoo%3Dbar" in url

    def test_redirect_url_encoding_mobile(self):
        url = bankid_autostart_url(self.TOKEN, self.REDIRECT, mobile=True)
        assert "https%3A%2F%2Fexample.com%2Fcallback%3Ffoo%3Dbar" in url

    def test_simple_redirect(self):
        url = bankid_autostart_url(self.TOKEN, "https://example.com")
        assert "redirect=https%3A%2F%2Fexample.com" in url


# ---------------------------------------------------------------------------
# hosted_login_url
# ---------------------------------------------------------------------------


class TestHostedLoginUrl:
    BASE = "https://id.tic.io"
    TENANT = "my-tenant"
    CALLBACK = "https://example.com/auth/callback"

    def test_required_params_only(self):
        url = hosted_login_url(self.BASE, self.TENANT, self.CALLBACK)
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "id.tic.io"
        assert parsed.path == "/my-tenant/login"
        qs = parse_qs(parsed.query)
        assert qs["callback"] == [self.CALLBACK]
        # provider=bankid is the default and should NOT appear in URL
        assert "provider" not in qs
        assert "state" not in qs
        assert "pnr" not in qs
        assert "lang" not in qs

    def test_all_optional_params(self):
        url = hosted_login_url(
            self.BASE,
            self.TENANT,
            self.CALLBACK,
            state="my-state-abc",
            provider="bankid",
            pnr="199001011234",
            lang="sv",
        )
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        assert qs["callback"] == [self.CALLBACK]
        assert qs["state"] == ["my-state-abc"]
        assert qs["pnr"] == ["199001011234"]
        assert qs["lang"] == ["sv"]
        # provider=bankid is default so should still be omitted
        assert "provider" not in qs

    def test_custom_provider(self):
        url = hosted_login_url(
            self.BASE,
            self.TENANT,
            self.CALLBACK,
            provider="freja",
        )
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        assert qs["provider"] == ["freja"]

    def test_trailing_slash_on_base_url(self):
        url = hosted_login_url("https://id.tic.io/", self.TENANT, self.CALLBACK)
        assert "/my-tenant/login?" in url
        assert "//my-tenant" not in url

    def test_state_only(self):
        url = hosted_login_url(
            self.BASE, self.TENANT, self.CALLBACK, state="session-xyz"
        )
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        assert qs["state"] == ["session-xyz"]
        assert "pnr" not in qs
        assert "lang" not in qs


# ---------------------------------------------------------------------------
# parse_callback
# ---------------------------------------------------------------------------


class TestParseCallback:
    def test_full_url_with_all_params(self):
        url = (
            "https://example.com/auth/callback"
            "?session_id=sess-001"
            "&token=jwt-xyz"
            "&state=my-state"
            "&signature=hmac-abc"
        )
        result = parse_callback(url)
        assert result == {
            "session_id": "sess-001",
            "token": "jwt-xyz",
            "state": "my-state",
            "signature": "hmac-abc",
        }

    def test_partial_params(self):
        url = "https://example.com/cb?session_id=sess-002&token=tok-123"
        result = parse_callback(url)
        assert result == {
            "session_id": "sess-002",
            "token": "tok-123",
        }
        assert "state" not in result
        assert "signature" not in result

    def test_no_recognized_params(self):
        url = "https://example.com/cb?foo=bar&baz=qux"
        result = parse_callback(url)
        assert result == {}

    def test_empty_query_string(self):
        url = "https://example.com/cb"
        result = parse_callback(url)
        assert result == {}

    def test_ignores_unknown_params(self):
        url = "https://example.com/cb?session_id=s1&unknown=val&token=t1"
        result = parse_callback(url)
        assert "unknown" not in result
        assert result["session_id"] == "s1"
        assert result["token"] == "t1"

    def test_takes_first_value_for_duplicated_param(self):
        url = "https://example.com/cb?session_id=first&session_id=second"
        result = parse_callback(url)
        assert result["session_id"] == "first"

    def test_session_id_only(self):
        url = "https://example.com/cb?session_id=sess-only"
        result = parse_callback(url)
        assert result == {"session_id": "sess-only"}
