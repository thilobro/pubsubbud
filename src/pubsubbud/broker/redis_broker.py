import json
from typing import AsyncGenerator

import redis.asyncio as redis

from pubsubbud.broker.broker_interface import BrokerInterface
from pubsubbud.config import RedisBrokerConfig
from pubsubbud.models import BrokerMessage


class RedisBroker(BrokerInterface):
    def __init__(self, config: RedisBrokerConfig) -> None:
        self._redis = redis.Redis(host=config.host, port=config.port)
        self._broker = self._redis.pubsub()

    async def subscribe(self, channel_name: str) -> None:
        await self._broker.subscribe(channel_name)

    async def unsubscribe(self, channel_name: str) -> None:
        await self._broker.unsubscribe(channel_name)

    async def publish(self, channel_name: str, message: str) -> None:
        await self._redis.publish(channel_name, json.dumps(message))

    async def close(self) -> None:
        pass

    async def read_messages(self) -> AsyncGenerator[BrokerMessage, None]:
        async for message in self._broker.listen():
            if "subscribe" not in message["type"]:
                payload = json.loads(json.loads(message["data"].decode()))
                yield BrokerMessage(**payload)
