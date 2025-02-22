import asyncio
import json
import logging
from typing import Any, Optional

import websockets
from websockets.asyncio.server import serve

from pubsubbud.config import WebsocketHandlerConfig
from pubsubbud.handler.handler_interface import HandlerInterface
from pubsubbud.models import BrokerMessage


class WebsocketConnection:
    def __init__(
        self, websocket: websockets.ServerConnection, logger: logging.Logger
    ) -> None:
        self._logger = logger
        self._websocket = websocket
        self._id = self._websocket.id

    async def send(self, message) -> None:
        await self._websocket.send(json.dumps(message))


class WebsocketHandler(HandlerInterface):
    def __init__(
        self,
        name: str,
        config: WebsocketHandlerConfig,
        logger: logging.Logger,
    ) -> None:
        super().__init__(name=name, publish_callback=self._send, logger=logger)
        self._config = config
        self._run_task: Optional[asyncio.Task] = None
        self._active_connections: dict[str, WebsocketConnection] = {}

    async def _serve(self) -> None:
        async with serve(
            self._handle_websocket, self._config.host, self._config.port
        ) as server:
            await server.serve_forever()

    def run(self) -> None:
        self._run_task = asyncio.create_task(self._serve())

    async def stop(self) -> None:
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.exceptions.CancelledError:
                self._logger.info(f"Interface {self._name} stopped.")

    async def _handle_websocket(self, websocket) -> None:
        try:
            self._connect(websocket)
            async for message in websocket:
                message = json.loads(message)
                message["header"]["origin_id"] = str(websocket.id)
                self._logger.info(f"Message received: {message}")
                await self._message_queue.put(BrokerMessage(**message))
        except (
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
        ):
            self._logger.error("Error in websocket handler.", exc_info=True)
        finally:
            self._disconnect(websocket)

    async def _send(
        self, handler_id: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        message = {"content": content, "header": header}
        await self._active_connections[handler_id].send(message)

    def _connect(self, websocket) -> None:
        self._active_connections[str(websocket.id)] = WebsocketConnection(
            websocket, self._logger
        )

    def _disconnect(self, websocket) -> None:
        del self._active_connections[str(websocket.id)]
        self.unsubscribe(handler_id=str(websocket.id))
