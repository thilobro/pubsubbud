import json
from typing import AsyncGenerator

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from pubsubbud.broker.broker_interface import BrokerInterface
from pubsubbud.config import KafkaBrokerConfig
from pubsubbud.models import BrokerMessage


class KafkaBroker(BrokerInterface):
    def __init__(self, config: KafkaBrokerConfig):
        port = config.port
        host = config.host
        server = f"{host}:{port}"
        self._consumer = AIOKafkaConsumer(bootstrap_servers=[server])
        self._producer = AIOKafkaProducer(bootstrap_servers=[server])
        self._is_producer_started = False

    async def subscribe(self, channel_name: str) -> None:
        channel_name = channel_name.replace("/", ".")
        subscriptions = self._consumer.subscription()
        new_topics = subscriptions | {channel_name}
        self._consumer.subscribe(list(new_topics))

    async def unsubscribe(self, channel_name: str) -> None:
        channel_name = channel_name.replace("/", ".")
        subscriptions = self._consumer.subscription()
        new_topics = subscriptions - channel_name
        self._consumer.unsubscribe(list(new_topics))

    async def publish(self, channel_name: str, message: str) -> None:
        channel_name = channel_name.replace("/", ".")
        if not self._is_producer_started:
            await self._producer.start()
            self._is_producer_started = True
        byte_message = json.dumps(message).encode("utf")
        await self._producer.send(channel_name, byte_message)

    async def close(self) -> None:
        await self._producer.stop()
        await self._consumer.stop()

    async def read_messages(self) -> AsyncGenerator[BrokerMessage, None]:
        await self._consumer.start()
        async for message in self._consumer:
            payload = json.loads(json.loads(message.value.decode()))
            yield BrokerMessage(**payload)
