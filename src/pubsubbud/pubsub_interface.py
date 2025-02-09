from abc import ABC, abstractmethod
from pubsubbud.custom_types import IFPublishCallback


class PubsubInterface(ABC):

    def __init__(self, publish_callback: IFPublishCallback) -> None:
        self._publish_callback = publish_callback
        self._subscribed_channels: dict[str, list[str]] = {}

    def subscribe(self, channel_name: str, interface_id: str) -> None:
        # TODO(handle multiple subscriptions to same channel)
        try:
            self._subscribed_channels[channel_name].append(interface_id)
        except KeyError:
            self._subscribed_channels[channel_name] = [interface_id]
        print(f"Subscribed to channel {channel_name} for interface {interface_id}")

    def unsubscribe(self, channel_name: str, interface_id: str) -> None:
        if interface_id:
            self._subscribed_channels[channel_name].remove(interface_id)
            if not self._subscribed_channels[channel_name]:
                del self._subscribed_channels[channel_name]
        else:
            del self._subscribed_channels[channel_name]

    async def publish_if_subscribed(self, channel_name, content, header) -> None:
        try:
            interface_ids = self._subscribed_channels[channel_name]
            print(f"PUBLISHING {channel_name} {interface_ids}")
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
