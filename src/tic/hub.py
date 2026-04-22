from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import websockets
import websockets.asyncio.client

from .exceptions import TicHubError
from .models import (
    AuthStatusResponse,
    CamelModel,
    Completed,
    ExtendResult,
    Failed,
    OrderRegenerated,
    StatusChanged,
    SubscribeResponse,
    TimeoutWarning,
)

RECORD_SEPARATOR = "\x1e"

logger = logging.getLogger("tic.hub")


class TicHub:
    """SignalR hub client for real-time BankID session updates.

    Implements the ASP.NET Core SignalR JSON Hub Protocol over WebSocket.
    """

    def __init__(
        self,
        base_url: str = "https://id.tic.io",
        *,
        auto_reconnect: bool = False,
        reconnect_delays: list[float] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._ws: websockets.asyncio.client.ClientConnection | None = None
        self._invocation_id = 0
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._listen_task: asyncio.Task[None] | None = None
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._connected = False
        self._auto_reconnect = auto_reconnect
        self._reconnect_delays = reconnect_delays or [0, 2, 10, 30]
        self._intentional_disconnect = False
        self._reconnected_handlers: list[Callable[..., Any]] = []
        self._disconnected_handlers: list[Callable[..., Any]] = []

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def _on_model(
        self, event: str, model_cls: type[CamelModel], handler: Callable
    ) -> None:
        def _wrap(*args: Any) -> Any:
            data = args[0] if args else {}
            return handler(model_cls.model_validate(data))

        self.on(event, _wrap)

    def on_qr_code(self, handler: Callable[[str], Any]) -> None:
        self.on("OnQRCode", handler)

    def on_status_changed(self, handler: Callable[[StatusChanged], Any]) -> None:
        self._on_model("OnStatusChanged", StatusChanged, handler)

    def on_completed(self, handler: Callable[[Completed], Any]) -> None:
        self._on_model("OnCompleted", Completed, handler)

    def on_failed(self, handler: Callable[[Failed], Any]) -> None:
        def _wrap(*args: Any) -> Any:
            hint_code = args[0] if len(args) > 0 else ""
            data = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            return handler(Failed.model_validate({**data, "hintCode": hint_code}))

        self.on("OnFailed", _wrap)

    def on_cancelled(self, handler: Callable[[], Any]) -> None:
        self.on("OnCancelled", lambda *_: handler())

    def on_timeout_warning(self, handler: Callable[[TimeoutWarning], Any]) -> None:
        self._on_model("OnTimeoutWarning", TimeoutWarning, handler)

    def on_order_regenerated(self, handler: Callable[[OrderRegenerated], Any]) -> None:
        self._on_model("OnOrderRegenerated", OrderRegenerated, handler)

    def on_reconnected(self, handler: Callable[[], Any]) -> None:
        self._reconnected_handlers.append(handler)

    def on_disconnected(self, handler: Callable[[], Any]) -> None:
        self._disconnected_handlers.append(handler)

    async def connect(self) -> None:
        hub_url = self.base_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        )
        hub_url = f"{hub_url}/hub"

        self._ws = await websockets.asyncio.client.connect(hub_url)

        handshake = json.dumps({"protocol": "json", "version": 1}) + RECORD_SEPARATOR
        await self._ws.send(handshake)

        raw = await self._ws.recv()
        if not isinstance(raw, str):
            raise TicHubError("Unexpected binary handshake response")
        for msg in raw.split(RECORD_SEPARATOR):
            if not msg.strip():
                continue
            resp = json.loads(msg)
            if "error" in resp:
                raise TicHubError(f"Handshake failed: {resp['error']}")

        self._connected = True
        self._listen_task = asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if not isinstance(raw, str):
                    continue
                for msg_str in raw.split(RECORD_SEPARATOR):
                    if not msg_str.strip():
                        continue
                    try:
                        msg = json.loads(msg_str)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse message: %s", msg_str[:200])
                        continue
                    self._handle_message(msg)
        except websockets.ConnectionClosed:
            logger.info("Hub connection closed")
        except Exception:
            logger.exception("Hub listener error")
        finally:
            self._connected = False
            for fut in self._pending.values():
                fut.cancel()
            self._pending.clear()
            self._fire_lifecycle_handlers(self._disconnected_handlers)
            if self._auto_reconnect and not self._intentional_disconnect:
                self._track_task(self._attempt_reconnect())

    def _track_task(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _handle_message(self, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")

        if msg_type == 6:
            self._track_task(self._send_raw({"type": 6}))
            return

        if msg_type == 7:
            logger.info("Server closed connection: %s", msg.get("error", ""))
            return

        if msg_type == 3:
            inv_id = msg.get("invocationId")
            if inv_id and inv_id in self._pending:
                fut = self._pending.pop(inv_id)
                if "error" in msg:
                    fut.set_exception(TicHubError(msg["error"]))
                else:
                    fut.set_result(msg.get("result"))
            return

        if msg_type == 1:
            target = msg.get("target", "")
            args = msg.get("arguments", [])
            for handler in self._handlers.get(target, []):
                try:
                    result = handler(*args)
                    if asyncio.iscoroutine(result):
                        self._track_task(result)
                except Exception:
                    logger.exception("Handler error for %s", target)

    async def _send_raw(self, msg: dict[str, Any]) -> None:
        if self._ws is None:
            raise TicHubError("Not connected")
        await self._ws.send(json.dumps(msg) + RECORD_SEPARATOR)

    async def _invoke(self, method: str, *args: Any) -> Any:
        self._invocation_id += 1
        inv_id = str(self._invocation_id)
        fut: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[inv_id] = fut
        await self._send_raw(
            {
                "type": 1,
                "invocationId": inv_id,
                "target": method,
                "arguments": list(args),
            }
        )
        return await fut

    async def subscribe(
        self, session_id: str, subscription_token: str
    ) -> SubscribeResponse:
        result = await self._invoke("Subscribe", session_id, subscription_token)
        return SubscribeResponse.from_api(result or {})

    async def cancel_session(self) -> None:
        await self._invoke("Cancel")

    async def get_qr_code(self) -> str | None:
        return await self._invoke("GetQRCode")

    async def get_status(self) -> AuthStatusResponse | None:
        data = await self._invoke("GetStatus")
        return AuthStatusResponse.from_api(data) if data else None

    async def extend_session(self) -> ExtendResult:
        data = await self._invoke("ExtendSession")
        return ExtendResult.from_api(data or {})

    def _fire_lifecycle_handlers(self, handlers: list[Callable[..., Any]]) -> None:
        for handler in handlers:
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    self._track_task(result)
            except Exception:
                logger.exception("Lifecycle handler error")

    async def _attempt_reconnect(self) -> None:
        for attempt, delay in enumerate(self._reconnect_delays):
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                await self.connect()
                logger.info("Reconnected on attempt %d", attempt + 1)
                self._fire_lifecycle_handlers(self._reconnected_handlers)
                return
            except Exception:
                logger.warning("Reconnect attempt %d failed", attempt + 1)
        logger.error("All reconnect attempts failed")

    async def reconnect(self) -> None:
        """Reconnect the WebSocket. Call subscribe() again with a fresh token afterward."""
        self._intentional_disconnect = True
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
        self._connected = False
        self._intentional_disconnect = False
        await self.connect()

    async def disconnect(self) -> None:
        self._intentional_disconnect = True
        for fut in self._pending.values():
            fut.cancel()
        self._pending.clear()
        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected
