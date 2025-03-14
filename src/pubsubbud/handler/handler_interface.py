import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterable, Optional

from pubsubbud.custom_types import HandlerPublishCallback
from pubsubbud.models import BrokerMessage


class HandlerInterface(ABC):
    def __init__(
        self,
        name: str,
        publish_callback: HandlerPublishCallback,
        logger: logging.Logger,
    ) -> None:
        self._name = name
        self._logger = logger
        self._message_queue: asyncio.Queue[BrokerMessage] = asyncio.Queue(maxsize=100)
        self._publish_callback = publish_callback
        self._subscribed_channels: dict[str, list[str]] = {}

    def subscribe(self, channel_name: str, handler_id: str) -> None:
        try:
            if handler_id in self._subscribed_channels[channel_name]:
                self._logger.info(
                    f"Handler {handler_id} is already subscribed to channel {channel_name}."
                )
                return None
            self._subscribed_channels[channel_name].append(handler_id)
        except KeyError:
            self._subscribed_channels[channel_name] = [handler_id]
        self._logger.info(
            f"Subscribed to channel {channel_name} for interface {handler_id}"
        )

    def unsubscribe(
        self, channel_name: Optional[str] = None, handler_id: Optional[str] = None
    ) -> None:
        if channel_name and not handler_id:
            del self._subscribed_channels[channel_name]
        elif channel_name and handler_id:
            self._subscribed_channels[channel_name].remove(handler_id)
            if not self._subscribed_channels[channel_name]:
                del self._subscribed_channels[channel_name]
        else:  # only handler id
            for channel_name, handler_ids in self._subscribed_channels.items():
                if handler_id in handler_ids:
                    self._subscribed_channels[channel_name].remove(handler_id)

    def has_subscribers(self, channel_name: str) -> bool:
        return channel_name in self._subscribed_channels.keys()

    async def publish(
        self, handler_id: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        await self._publish_callback(handler_id, content, header)

    async def publish_if_subscribed(self, channel_name, content, header) -> None:
        if self.has_subscribers(channel_name):
            interface_ids = self._subscribed_channels[channel_name]
            for interface_id in interface_ids:
                try:
                    await self._publish_callback(interface_id, content, header)
                except Exception:
                    # TODO: here we should catch a custom exception
                    # thrown when the target does not respond,
                    # then we disconnect said target
                    pass

    async def _message_iterator(self) -> AsyncIterable:
        while True:
            message = await self._message_queue.get()
            yield message

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        pass

    @property
    def name(self) -> str:
        return self._name

    @property
    def message_iterator(self) -> Optional[AsyncIterable]:
        return self._message_iterator()
