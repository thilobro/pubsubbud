import asyncio
import http
import json
import logging
from typing import Any, Optional

from pubsubbud.broker.broker_interface import BrokerInterface
from pubsubbud.config import PubsubManagerConfig
from pubsubbud.custom_types import CBHandlerCallback
from pubsubbud.handler.handler_interface import HandlerInterface
from pubsubbud.helpers import create_header
from pubsubbud.models import BrokerMessage


class PubsubManager:
    def __init__(
        self,
        config: PubsubManagerConfig,
        broker: BrokerInterface,
        logger: logging.Logger,
    ) -> None:
        self._logger = logger
        self._channels: list[str] = []
        self._callbacks: dict[str, list[CBHandlerCallback]] = {}
        self._uuid = config.uuid
        self._broker = broker
        self._handlers: dict[str, HandlerInterface] = {}
        self._handler_tasks: dict[str, asyncio.Task] = {}

    async def _add_channel(self, channel_name: str) -> None:
        if channel_name not in self._channels:
            await self._broker.subscribe(channel_name)
            await self._broker.subscribe(f"{self._uuid}/{channel_name}")
            self._channels.append(channel_name)

    async def _remove_channel(self, channel_name: str) -> None:
        if channel_name in self._channels:
            await self._broker.unsubscribe(channel_name)
            await self._broker.unsubscribe(f"{self._uuid}/{channel_name}")
            self._channels.remove(channel_name)

    async def register_callback(
        self, channel_name: str, callback: CBHandlerCallback
    ) -> None:
        try:
            self._callbacks[channel_name].append(callback)
        except KeyError:
            self._callbacks[channel_name] = [callback]
        await self._add_channel(channel_name)

    async def unregister_callback(
        self, channel_name: str, callback: Optional[CBHandlerCallback]
    ) -> None:
        # TODO: remove channels
        try:
            if callback:
                self._callbacks[channel_name].remove(callback)
                if not self._callbacks[channel_name]:
                    del self._callbacks[channel_name]
            else:
                del self._callbacks[channel_name]
        except KeyError:
            self._logger.warning(
                f"Unable to unregister callbacks to channel name {channel_name}."
            )

    async def _subscribe(
        self,
        channel_name: str,
        handler_name: Optional[str] = None,
        handler_id: Optional[str] = None,
    ) -> None:
        if handler_id and handler_name:
            self._handlers[handler_name].subscribe(channel_name, handler_id)
        await self._add_channel(channel_name)

    async def _unsubscribe(
        self,
        channel_name: str,
        handler_name: Optional[str] = None,
        handler_id: Optional[str] = None,
    ) -> None:
        if handler_name:
            self._handlers[handler_name].unsubscribe(channel_name, handler_id)
        else:
            for handler in self._handlers.values():
                handler.unsubscribe(channel_name, handler_id)
        if not self._has_subscribers(channel_name):
            await self._remove_channel(channel_name)

    def _has_subscribers(self, channel_name: str) -> bool:
        for handler in self._handlers.values():
            if handler.has_subscribers(channel_name):
                return True
        return False

    def _run_message_task(self) -> None:
        self._message_task = asyncio.create_task(self._read_messages())

    async def _handle_subscription_message(
        self, message: BrokerMessage, handler_name: str, handler_id: str
    ) -> None:
        subscription_type = message.content["subscription_type"]
        subscription_channel = message.content["subscription_channel"]
        if subscription_type == "subscription":
            await self._subscribe(subscription_channel, handler_name, handler_id)
        elif subscription_type == "unsubscription":
            await self._unsubscribe(subscription_channel, handler_name, handler_id)
        else:
            raise ValueError(f"Subscription type not supported: {subscription_type}.")

    async def _handle_pubsub_message(self, message: BrokerMessage) -> None:
        channel_name = message.header.channel
        content = message.content
        await self.publish(channel_name, content, True)

    def _run_handler_tasks(self) -> None:
        for handler in self._handlers.values():
            handler.run()
            self._handler_tasks[handler.name] = asyncio.create_task(
                self._get_handler_messages(handler)
            )

    async def _get_handler_messages(self, handler):
        async for message, handler_id in handler.message_iterator:  # type: ignore
            try:
                channel_name = message.header.channel
                message_id = message.header.message_id
                self._logger.info(f"Message from handler {handler.name}: {message}")
                if channel_name == "subscription":
                    await self._handle_subscription_message(
                        message, handler.name, handler_id
                    )
                else:
                    await self._handle_pubsub_message(message)
                ack_header = {
                    "ack_id": message_id,
                    "status_code": http.HTTPStatus.OK,
                }
            except Exception:
                ack_header = {
                    "ack_id": message_id,
                    "status_code": http.HTTPStatus.INTERNAL_SERVER_ERROR,
                }
            finally:
                await handler.publish(handler_id, {}, ack_header)

    def run(self) -> None:
        self._run_message_task()
        self._run_handler_tasks()

    async def _execute_callbacks(
        self, channel_name: str, content: dict[str, Any], header: dict[str, Any]
    ):
        callbacks = self._callbacks[channel_name]
        for callback in callbacks:
            await callback(content, header)

    async def _read_messages(self) -> None:
        async for message in self._broker.read_messages():
            if message:
                header = message.header
                channel_name = header.channel
                content = message.content
                self._logger.info(f"Message from broker: {message}")
                if "/" in channel_name:
                    channel_name = channel_name.split("/")[1]
                await self._forward_to_handlers(channel_name, content, header)
                await self._execute_callbacks(channel_name, content, header.dict())

    async def _forward_to_handlers(self, channel, content, header) -> None:
        for handler in self._handlers.values():
            await handler.publish_if_subscribed(channel, content, header.dict())

    def add_handler(self, handler: HandlerInterface) -> None:
        self._handlers[handler.name] = handler

    async def close(self) -> None:
        self._logger.info("Closing pubsub.")
        self._message_task.cancel()
        for task in self._handler_tasks.values():
            task.cancel()
        for handler in self._handlers.values():
            await handler.stop()
        await self._broker.close()

    async def publish(
        self, channel_name: str, data: dict[str, Any], internal: bool = False
    ) -> None:
        message = {}
        message["content"] = data
        message["header"] = create_header(channel_name)
        if internal:
            channel_name = f"{self._uuid}/{channel_name}"
        self._logger.debug(f"Message to redis: {message}, {channel_name}")
        await self._broker.publish(channel_name, json.dumps(message))
