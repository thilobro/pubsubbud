import logging
from abc import ABC, abstractmethod
from typing import Optional

from pubsubbud.custom_types import IFPublishCallback


class PubsubInterface(ABC):
    def __init__(
        self, name: str, publish_callback: IFPublishCallback, logger: logging.Logger
    ) -> None:
        self._name = name
        self._logger = logger
        self._publish_callback = publish_callback
        self._subscribed_channels: dict[str, list[str]] = {}

    def subscribe(self, channel_name: str, interface_id: str) -> None:
        try:
            if interface_id in self._subscribed_channels[channel_name]:
                self._logger.info(
                    f"Interface {interface_id} is already subscribed to channel {channel_name}."
                )
                return None
            self._subscribed_channels[channel_name].append(interface_id)
        except KeyError:
            self._subscribed_channels[channel_name] = [interface_id]
        self._logger.info(
            f"Subscribed to channel {channel_name} for interface {interface_id}"
        )

    def unsubscribe(self, channel_name: str, interface_id: Optional[str]) -> None:
        if interface_id:
            self._subscribed_channels[channel_name].remove(interface_id)
            if not self._subscribed_channels[channel_name]:
                del self._subscribed_channels[channel_name]
        else:
            del self._subscribed_channels[channel_name]

    def has_subscribers(self, channel_name: str) -> bool:
        return channel_name in self._subscribed_channels.keys()

    async def publish_if_subscribed(self, channel_name, content, header) -> None:
        if self.has_subscribers(channel_name):
            try:
                interface_ids = self._subscribed_channels[channel_name]
                for interface_id in interface_ids:
                    await self._publish_callback(interface_id, content, header)
            except Exception:
                pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        pass

    @property
    def name(self) -> str:
        return self._name
