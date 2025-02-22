from abc import ABC, abstractmethod
from typing import AsyncGenerator

from pubsubbud.models import BrokerMessage, BrokerMessageHeader


class BrokerInterface(ABC):
    @abstractmethod
    async def subscribe(self, channel_name: str) -> None:
        pass

    @abstractmethod
    async def unsubscribe(self, channel_name: str) -> None:
        pass

    @abstractmethod
    async def publish(self, channel_name: str, message: str) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def read_messages(self) -> AsyncGenerator[BrokerMessage, None]:
        header = BrokerMessageHeader(message_id="1", channel="dummy", origin_id="dummy")
        yield BrokerMessage(header=header, content={"dummy": 1})
