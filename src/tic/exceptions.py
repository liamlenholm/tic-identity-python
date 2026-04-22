from __future__ import annotations


class TicError(Exception):
    pass


class TicAPIError(TicError):
    def __init__(
        self, status_code: int, code: str, message: str, details: dict | None = None
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{status_code}] {code}: {message}")


class TicHubError(TicError):
    pass


class TicWebhookError(TicError):
    pass
