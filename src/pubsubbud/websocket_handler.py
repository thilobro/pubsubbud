import asyncio
import json
import logging
from typing import Any, Optional

import websockets
from websockets.asyncio.server import serve

from pubsubbud.config import WebsocketHandlerConfig
from pubsubbud.custom_types import (
    ProcessMessageCallback,
    SubscriptionCallback,
    UnsubscriptionCallback,
)
from pubsubbud.pubsub_interface import PubsubInterface


class WebsocketConnection:
    def __init__(self, websocket: websockets.ServerConnection) -> None:
        self._websocket = websocket

    async def send(self, message) -> None:
        await self._websocket.send(json.dumps(message))


class WebsocketHandler(PubsubInterface):
    def __init__(
        self,
        name: str,
        process_message_callback: ProcessMessageCallback,
        subscription_callback: SubscriptionCallback,
        unsubscription_callback: UnsubscriptionCallback,
        config: WebsocketHandlerConfig,
        logger: logging.Logger,
    ) -> None:
        super().__init__(name=name, publish_callback=self._send, logger=logger)
        self._config = config
        self._run_task: Optional[asyncio.Task] = None
        self._active_connections: dict[str, WebsocketConnection] = {}
        self._process_message_callback = process_message_callback
        self._subcription_callback = subscription_callback
        self._unsubscription_callback = unsubscription_callback

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
            await self._run_task

    async def _handle_subscription_message(
        self, message: dict[str, Any], interface_id: str
    ) -> None:
        subscription_type = message["subscription_type"]
        subscription_channel = message["subscription_channel"]
        if subscription_type == "subscription":
            await self._subcription_callback(
                subscription_channel, self._name, interface_id
            )
        elif subscription_type == "unsubscription":
            await self._unsubscription_callback(
                subscription_channel, self._name, interface_id
            )
        else:
            raise ValueError(f"Subscription type not supported: {subscription_type}.")

    async def _handle_pubsub_message(self, message: dict[str, Any]) -> None:
        channel = message["channel"]
        data = message["data"]
        await self._process_message_callback(channel, data, True)

    async def _handle_websocket(self, websocket) -> None:
        try:
            self._connect(websocket)
            async for message in websocket:
                message = json.loads(message)
                self._logger.info(f"Message received: {message}")
                message_type = message["type"]
                if message_type == "subscription":
                    await self._handle_subscription_message(message, websocket.id)
                elif message_type == "pubsub":
                    await self._handle_pubsub_message(message)
        except (
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
        ):
            self._logger.error("Error in websocket handler.", exc_info=True)
        finally:
            self._disconnect(websocket)

    async def _send(
        self, interface_id: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        message = {"content": content, "header": header}
        await self._active_connections[interface_id].send(message)

    def _connect(self, websocket) -> None:
        self._active_connections[websocket.id] = WebsocketConnection(websocket)

    def _disconnect(self, websocket) -> None:
        del self._active_connections[websocket.id]
