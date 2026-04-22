"""Tests for tic.hub — TicHub handler registration and _handle_message dispatch."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tic.exceptions import TicHubError
from tic.hub import TicHub
from tic.models import (
    Completed,
    Failed,
    OrderRegenerated,
    StatusChanged,
    TimeoutWarning,
    User,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def hub() -> TicHub:
    return TicHub(base_url="https://id.tic.io")


# ---------------------------------------------------------------------------
# Handler registration via .on()
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    def test_on_registers_handler(self, hub: TicHub):
        handler = MagicMock()
        hub.on("CustomEvent", handler)
        assert "CustomEvent" in hub._handlers
        assert handler in hub._handlers["CustomEvent"]

    def test_on_multiple_handlers(self, hub: TicHub):
        h1 = MagicMock()
        h2 = MagicMock()
        hub.on("MyEvent", h1)
        hub.on("MyEvent", h2)
        assert len(hub._handlers["MyEvent"]) == 2

    def test_on_qr_code(self, hub: TicHub):
        handler = MagicMock()
        hub.on_qr_code(handler)
        assert "OnQRCode" in hub._handlers

    def test_on_status_changed(self, hub: TicHub):
        handler = MagicMock()
        hub.on_status_changed(handler)
        assert "OnStatusChanged" in hub._handlers

    def test_on_completed(self, hub: TicHub):
        handler = MagicMock()
        hub.on_completed(handler)
        assert "OnCompleted" in hub._handlers

    def test_on_failed(self, hub: TicHub):
        handler = MagicMock()
        hub.on_failed(handler)
        assert "OnFailed" in hub._handlers

    def test_on_cancelled(self, hub: TicHub):
        handler = MagicMock()
        hub.on_cancelled(handler)
        assert "OnCancelled" in hub._handlers

    def test_on_timeout_warning(self, hub: TicHub):
        handler = MagicMock()
        hub.on_timeout_warning(handler)
        assert "OnTimeoutWarning" in hub._handlers

    def test_on_order_regenerated(self, hub: TicHub):
        handler = MagicMock()
        hub.on_order_regenerated(handler)
        assert "OnOrderRegenerated" in hub._handlers


# ---------------------------------------------------------------------------
# _handle_message — Invocation (type 1)
# ---------------------------------------------------------------------------


class TestHandleInvocation:
    def test_dispatches_to_raw_handler(self, hub: TicHub):
        handler = MagicMock()
        hub.on("TestEvent", handler)
        hub._handle_message(
            {
                "type": 1,
                "target": "TestEvent",
                "arguments": ["arg1", "arg2"],
            }
        )
        handler.assert_called_once_with("arg1", "arg2")

    def test_dispatches_to_multiple_handlers(self, hub: TicHub):
        h1 = MagicMock()
        h2 = MagicMock()
        hub.on("TestEvent", h1)
        hub.on("TestEvent", h2)
        hub._handle_message(
            {
                "type": 1,
                "target": "TestEvent",
                "arguments": ["data"],
            }
        )
        h1.assert_called_once_with("data")
        h2.assert_called_once_with("data")

    def test_no_handler_does_not_raise(self, hub: TicHub):
        # Should silently ignore unknown events
        hub._handle_message(
            {
                "type": 1,
                "target": "UnknownEvent",
                "arguments": [],
            }
        )

    def test_empty_arguments(self, hub: TicHub):
        handler = MagicMock()
        hub.on("NoArgs", handler)
        hub._handle_message(
            {
                "type": 1,
                "target": "NoArgs",
                "arguments": [],
            }
        )
        handler.assert_called_once_with()

    def test_handler_exception_does_not_propagate(self, hub: TicHub):
        handler = MagicMock(side_effect=ValueError("boom"))
        hub.on("Broken", handler)
        # Should not raise, the exception is caught and logged
        hub._handle_message(
            {
                "type": 1,
                "target": "Broken",
                "arguments": [],
            }
        )
        handler.assert_called_once()


# ---------------------------------------------------------------------------
# _handle_message — Ping (type 6)
# ---------------------------------------------------------------------------


class TestHandlePing:
    async def test_ping_sends_pong(self, hub: TicHub):
        with patch.object(hub, "_send_raw", new_callable=AsyncMock) as mock_send:
            hub._handle_message({"type": 6})
            # Let the event loop process the task created by _handle_message
            await asyncio.sleep(0)
            mock_send.assert_called_once_with({"type": 6})


# ---------------------------------------------------------------------------
# _handle_message — Close (type 7)
# ---------------------------------------------------------------------------


class TestHandleClose:
    def test_close_message_does_not_raise(self, hub: TicHub):
        hub._handle_message({"type": 7, "error": "Server shutting down"})

    def test_close_message_without_error(self, hub: TicHub):
        hub._handle_message({"type": 7})


# ---------------------------------------------------------------------------
# _handle_message — Completion (type 3)
# ---------------------------------------------------------------------------


class TestHandleCompletion:
    def test_completion_resolves_future(self, hub: TicHub):
        loop = asyncio.new_event_loop()
        fut: asyncio.Future = loop.create_future()
        hub._pending["42"] = fut
        hub._handle_message(
            {
                "type": 3,
                "invocationId": "42",
                "result": {"some": "data"},
            }
        )
        assert fut.done()
        assert fut.result() == {"some": "data"}
        loop.close()

    def test_completion_with_error(self, hub: TicHub):
        loop = asyncio.new_event_loop()
        fut: asyncio.Future = loop.create_future()
        hub._pending["43"] = fut
        hub._handle_message(
            {
                "type": 3,
                "invocationId": "43",
                "error": "Something went wrong",
            }
        )
        assert fut.done()
        with pytest.raises(TicHubError, match="Something went wrong"):
            fut.result()
        loop.close()

    def test_completion_unknown_invocation_id(self, hub: TicHub):
        # Should not raise for unknown invocation IDs
        hub._handle_message(
            {
                "type": 3,
                "invocationId": "999",
                "result": None,
            }
        )

    def test_completion_without_invocation_id(self, hub: TicHub):
        # Should not raise when invocationId is missing
        hub._handle_message({"type": 3, "result": None})


# ---------------------------------------------------------------------------
# Typed event handlers — wrapper correctness
# ---------------------------------------------------------------------------


class TestTypedEventHandlers:
    def test_on_status_changed_wraps_data(self, hub: TicHub):
        received: list[StatusChanged] = []
        hub.on_status_changed(lambda sc: received.append(sc))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnStatusChanged",
                "arguments": [
                    {
                        "status": "pending",
                        "hintCode": "outstandingTransaction",
                        "message": "Waiting for BankID",
                        "messageEn": "Waiting for BankID",
                    }
                ],
            }
        )
        assert len(received) == 1
        sc = received[0]
        assert isinstance(sc, StatusChanged)
        assert sc.status == "pending"
        assert sc.hint_code == "outstandingTransaction"
        assert sc.message == "Waiting for BankID"
        assert sc.message_en == "Waiting for BankID"

    def test_on_status_changed_empty_args_logs_error(self, hub: TicHub):
        received: list[StatusChanged] = []
        hub.on_status_changed(lambda sc: received.append(sc))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnStatusChanged",
                "arguments": [],
            }
        )
        assert len(received) == 0

    def test_on_completed_wraps_data(self, hub: TicHub):
        received: list[Completed] = []
        hub.on_completed(lambda c: received.append(c))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnCompleted",
                "arguments": [
                    {
                        "sessionId": "sess-001",
                        "status": "complete",
                        "user": {
                            "personalNumber": "199001011234",
                            "givenName": "Anna",
                            "surname": "Svensson",
                            "name": "Anna Svensson",
                        },
                        "completedAt": "2026-06-15T12:01:00Z",
                    }
                ],
            }
        )
        assert len(received) == 1
        c = received[0]
        assert isinstance(c, Completed)
        assert c.session_id == "sess-001"
        assert c.status == "complete"
        assert isinstance(c.user, User)
        assert c.user.given_name == "Anna"
        assert c.user.personal_number == "199001011234"

    def test_on_failed_wraps_data(self, hub: TicHub):
        received: list[Failed] = []
        hub.on_failed(lambda f: received.append(f))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnFailed",
                "arguments": [
                    "userCancel",
                    {"message": "User cancelled", "messageEn": "User cancelled"},
                ],
            }
        )
        assert len(received) == 1
        f = received[0]
        assert isinstance(f, Failed)
        assert f.hint_code == "userCancel"
        assert f.message == "User cancelled"
        assert f.message_en == "User cancelled"

    def test_on_failed_single_arg(self, hub: TicHub):
        received: list[Failed] = []
        hub.on_failed(lambda f: received.append(f))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnFailed",
                "arguments": ["startFailed"],
            }
        )
        assert len(received) == 1
        assert received[0].hint_code == "startFailed"
        assert received[0].message is None

    def test_on_cancelled_calls_handler(self, hub: TicHub):
        called = []
        hub.on_cancelled(lambda: called.append(True))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnCancelled",
                "arguments": [],
            }
        )
        assert called == [True]

    def test_on_timeout_warning_wraps_data(self, hub: TicHub):
        received: list[TimeoutWarning] = []
        hub.on_timeout_warning(lambda tw: received.append(tw))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnTimeoutWarning",
                "arguments": [{"secondsRemaining": 30, "canExtend": True}],
            }
        )
        assert len(received) == 1
        tw = received[0]
        assert isinstance(tw, TimeoutWarning)
        assert tw.seconds_remaining == 30
        assert tw.can_extend is True

    def test_on_order_regenerated_wraps_data(self, hub: TicHub):
        received: list[OrderRegenerated] = []
        hub.on_order_regenerated(lambda o: received.append(o))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnOrderRegenerated",
                "arguments": [
                    {
                        "orderCount": 3,
                        "maxOrders": 5,
                        "sessionExpiresInSeconds": 180,
                    }
                ],
            }
        )
        assert len(received) == 1
        o = received[0]
        assert isinstance(o, OrderRegenerated)
        assert o.order_count == 3
        assert o.max_orders == 5
        assert o.session_expires_in_seconds == 180

    def test_on_qr_code_passes_string(self, hub: TicHub):
        received: list[str] = []
        hub.on_qr_code(lambda qr: received.append(qr))
        hub._handle_message(
            {
                "type": 1,
                "target": "OnQRCode",
                "arguments": ["bankid.xxxx.yyyy.zzzz"],
            }
        )
        assert received == ["bankid.xxxx.yyyy.zzzz"]


# ---------------------------------------------------------------------------
# Unknown / malformed message types
# ---------------------------------------------------------------------------


class TestUnknownMessageTypes:
    def test_unknown_type_does_not_raise(self, hub: TicHub):
        hub._handle_message({"type": 99})

    def test_none_type_does_not_raise(self, hub: TicHub):
        hub._handle_message({"some": "data"})

    def test_missing_target_in_invocation(self, hub: TicHub):
        # type 1 without target — should not crash
        hub._handle_message({"type": 1, "arguments": ["x"]})


# ---------------------------------------------------------------------------
# Hub properties
# ---------------------------------------------------------------------------


class TestHubProperties:
    def test_initial_state(self, hub: TicHub):
        assert hub.connected is False
        assert hub._ws is None
        assert hub._invocation_id == 0
        assert hub._pending == {}
        assert hub._handlers == {}

    def test_base_url_trailing_slash_stripped(self):
        h = TicHub(base_url="https://id.tic.io/")
        assert h.base_url == "https://id.tic.io"


# ---------------------------------------------------------------------------
# _send_raw guard
# ---------------------------------------------------------------------------


class TestSendRawGuard:
    async def test_send_raw_raises_when_not_connected(self, hub: TicHub):
        with pytest.raises(TicHubError, match="Not connected"):
            await hub._send_raw({"type": 6})


# ---------------------------------------------------------------------------
# Lifecycle callbacks — on_reconnected / on_disconnected
# ---------------------------------------------------------------------------


class TestLifecycleCallbacks:
    def test_on_reconnected_registers_handler(self, hub: TicHub):
        handler = MagicMock()
        hub.on_reconnected(handler)
        assert handler in hub._reconnected_handlers

    def test_on_disconnected_registers_handler(self, hub: TicHub):
        handler = MagicMock()
        hub.on_disconnected(handler)
        assert handler in hub._disconnected_handlers

    def test_fire_lifecycle_handlers_sync(self, hub: TicHub):
        called = []
        hub._disconnected_handlers.append(lambda: called.append("fired"))
        hub._fire_lifecycle_handlers(hub._disconnected_handlers)
        assert called == ["fired"]

    async def test_fire_lifecycle_handlers_async(self, hub: TicHub):
        called = []

        async def async_handler():
            called.append("async_fired")

        hub._reconnected_handlers.append(async_handler)
        hub._fire_lifecycle_handlers(hub._reconnected_handlers)
        await asyncio.sleep(0)
        assert called == ["async_fired"]

    def test_fire_lifecycle_handler_exception_does_not_propagate(self, hub: TicHub):
        handler = MagicMock(side_effect=RuntimeError("boom"))
        hub._disconnected_handlers.append(handler)
        hub._fire_lifecycle_handlers(hub._disconnected_handlers)
        handler.assert_called_once()


# ---------------------------------------------------------------------------
# Auto-reconnect constructor options
# ---------------------------------------------------------------------------


class TestAutoReconnectConfig:
    def test_default_auto_reconnect_off(self):
        h = TicHub()
        assert h._auto_reconnect is False

    def test_auto_reconnect_enabled(self):
        h = TicHub(auto_reconnect=True)
        assert h._auto_reconnect is True

    def test_custom_reconnect_delays(self):
        h = TicHub(reconnect_delays=[1, 5, 15])
        assert h._reconnect_delays == [1, 5, 15]

    def test_default_reconnect_delays(self):
        h = TicHub()
        assert h._reconnect_delays == [0, 2, 10, 30]

    def test_intentional_disconnect_initially_false(self):
        h = TicHub()
        assert h._intentional_disconnect is False
