import asyncio
import http
import json
import logging
import uuid
from typing import Any, Optional

import redis.asyncio as redis

from pubsubbud.config import PubsubHandlerConfig
from pubsubbud.pubsub_interface import PubsubInterface


def create_header(channel: str) -> dict[str, Any]:
    header = {}
    header["_id"] = str(uuid.uuid4())
    header["channel"] = channel
    return header


class PubsubHandler:
    def __init__(self, config: PubsubHandlerConfig, logger: logging.Logger) -> None:
        self._logger = logger
        self._uuid = config.uuid
        self._redis = redis.Redis()
        self._pubsub = self._redis.pubsub()
        self._interfaces: dict[str, PubsubInterface] = {}
        self._interface_tasks: dict[str, asyncio.Task] = {}

    async def subscribe(
        self,
        channel_name: str,
        interface_name: Optional[str] = None,
        interface_id: Optional[str] = None,
    ) -> None:
        if interface_id and interface_name:
            self._interfaces[interface_name].subscribe(channel_name, interface_id)
        await self._pubsub.subscribe(channel_name)
        await self._pubsub.subscribe(f"{self._uuid}/{channel_name}")

    async def unsubscribe(
        self,
        channel_name: str,
        interface_name: Optional[str] = None,
        interface_id: Optional[str] = None,
    ) -> None:
        if interface_name:
            self._interfaces[interface_name].unsubscribe(channel_name, interface_id)
        else:
            for interface in self._interfaces.values():
                interface.unsubscribe(channel_name, interface_id)
        if not self._has_subscribers(channel_name):
            await self._pubsub.unsubscribe(channel_name)
            await self._pubsub.unsubscribe(f"{self._uuid}/{channel_name}")

    def _has_subscribers(self, channel_name: str) -> bool:
        for interface in self._interfaces.values():
            if interface.has_subscribers(channel_name):
                return True
        return False

    def _run_message_task(self) -> None:
        self._message_task = asyncio.create_task(self._read_messages())

    async def _handle_subscription_message(
        self, message: dict[str, Any], interface_name: str, interface_id: str
    ) -> None:
        subscription_type = message["subscription_type"]
        subscription_channel = message["subscription_channel"]
        if subscription_type == "subscription":
            await self.subscribe(subscription_channel, interface_name, interface_id)
        elif subscription_type == "unsubscription":
            await self.unsubscribe(subscription_channel, interface_name, interface_id)
        else:
            raise ValueError(f"Subscription type not supported: {subscription_type}.")

    async def _handle_pubsub_message(self, message: dict[str, Any]) -> None:
        channel = message["channel"]
        data = message["data"]
        await self.publish(channel, data, True)

    def _run_interface_tasks(self) -> None:
        for interface in self._interfaces.values():
            interface.run()
            if interface.message_iterator:

                async def _get_interface_messages():
                    async for message, interface_id in interface.message_iterator:  # type: ignore
                        message_id = None
                        try:
                            message_type = message["type"]
                            message_id = message["_id"]
                            if message_type == "subscription":
                                await self._handle_subscription_message(
                                    message, interface.name, interface_id
                                )
                            elif message_type == "pubsub":
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
                            await interface.publish(interface_id, {}, ack_header)

                self._interface_tasks[interface.name] = asyncio.create_task(
                    _get_interface_messages()
                )

    def run(self) -> None:
        self._run_message_task()
        self._run_interface_tasks()

    async def _run(self) -> None:
        message_task = asyncio.create_task(self._read_messages())
        try:
            await message_task
        except asyncio.CancelledError:
            self._logger.info("Pubsub cancelled.")
            if not message_task.cancelled():
                message_task.cancel()

    async def _read_messages(self) -> None:
        async for message in self._pubsub.listen():
            if message and not message["type"] == "subscribe":
                self._logger.debug(f"Message from redis: {message}")
                channel = message["channel"].decode()
                if "/" in channel:
                    channel = channel.split("/")[1]
                data = json.loads(message["data"].decode())
                content = data["content"]
                header = data["header"]
                await self._forward_to_interfaces(channel, content, header)
        raise asyncio.CancelledError()

    async def _forward_to_interfaces(self, channel, content, header) -> None:
        for interface in self._interfaces.values():
            await interface.publish_if_subscribed(channel, content, header)

    def add_interface(self, interface: PubsubInterface) -> None:
        self._interfaces[interface.name] = interface

    async def close(self) -> None:
        self._logger.info("Closing pubsub.")
        self._message_task.cancel()
        for task in self._interface_tasks.values():
            task.cancel()
        for interface in self._interfaces.values():
            await interface.stop()
        await self._pubsub.close()

    async def publish(
        self, channel, data: dict[str, Any], internal: bool = False
    ) -> None:
        message = {}
        message["content"] = data
        message["header"] = create_header(channel)
        if internal:
            channel = f"{self._uuid}/{channel}"
        self._logger.debug(f"Message to redis: {message}, {channel}")
        await self._redis.publish(channel, json.dumps(message))
