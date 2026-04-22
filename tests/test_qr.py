"""Tests for tic.qr — BankID animated QR code data generation."""

from __future__ import annotations

import hashlib
import hmac

from tic.qr import generate_qr_data


class TestGenerateQrData:
    TOKEN = "67df3917-fa0d-44e5-b327-edcc928297f8"
    SECRET = "d28db9a7-4cde-429e-a983-359be676944c"

    def test_returns_correct_format(self):
        result = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=0)
        parts = result.split(".")
        assert len(parts) == 4
        assert parts[0] == "bankid"
        assert parts[1] == self.TOKEN
        assert parts[2] == "0"

    def test_hmac_is_valid_sha256_hex(self):
        result = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=5)
        hmac_hex = result.split(".")[3]
        assert len(hmac_hex) == 64  # SHA-256 produces 64 hex chars
        int(hmac_hex, 16)  # should not raise

    def test_hmac_is_deterministic(self):
        r1 = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=3)
        r2 = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=3)
        assert r1 == r2

    def test_different_elapsed_seconds_produce_different_data(self):
        r0 = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=0)
        r1 = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=1)
        r2 = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=2)
        assert r0 != r1
        assert r1 != r2
        assert r0 != r2

    def test_elapsed_seconds_zero(self):
        result = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=0)
        assert ".0." in result

    def test_token_appears_in_output(self):
        result = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=10)
        assert self.TOKEN in result

    def test_secret_does_not_appear_in_output(self):
        result = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=10)
        assert self.SECRET not in result

    def test_matches_manual_hmac_computation(self):
        elapsed = 7
        expected_hmac = hmac.new(
            self.SECRET.encode("utf-8"),
            str(elapsed).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        expected = f"bankid.{self.TOKEN}.{elapsed}.{expected_hmac}"

        result = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=elapsed)
        assert result == expected

    def test_different_secrets_produce_different_hmacs(self):
        r1 = generate_qr_data(self.TOKEN, "secret-aaa", elapsed_seconds=1)
        r2 = generate_qr_data(self.TOKEN, "secret-bbb", elapsed_seconds=1)
        assert r1.split(".")[3] != r2.split(".")[3]

    def test_large_elapsed_seconds(self):
        result = generate_qr_data(self.TOKEN, self.SECRET, elapsed_seconds=9999)
        parts = result.split(".")
        assert parts[2] == "9999"
        assert len(parts[3]) == 64
