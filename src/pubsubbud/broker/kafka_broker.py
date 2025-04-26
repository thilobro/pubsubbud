import json
from typing import AsyncGenerator

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from pubsubbud.broker.broker_interface import BrokerInterface
from pubsubbud.config import KafkaBrokerConfig
from pubsubbud.models import BrokerMessage


class KafkaBroker(BrokerInterface):
    """Kafka implementation of the broker interface.

    This class implements the BrokerInterface using Kafka as the underlying
    message broker. It uses the aiokafka library for async communication.

    Attributes:
        _consumer: Kafka consumer instance for receiving messages
        _producer: Kafka producer instance for sending messages
        _is_producer_started: Flag indicating if the producer has been started
    """

    def __init__(self, config: KafkaBrokerConfig):
        """Initialize the Kafka broker.

        Args:
            config: Configuration for the Kafka broker connection
        """
        port = config.port
        host = config.host
        server = f"{host}:{port}"
        self._consumer = AIOKafkaConsumer(bootstrap_servers=[server])
        self._producer = AIOKafkaProducer(bootstrap_servers=[server])
        self._is_producer_started = False

    async def subscribe(self, channel_name: str) -> None:
        """Subscribe to a Kafka topic.

        Args:
            channel_name: The Kafka topic to subscribe to

        Note:
            Channel names with '/' are converted to '.' as Kafka topics
            don't support '/' characters.
        """
        channel_name = channel_name.replace("/", ".")
        subscriptions = self._consumer.subscription()
        new_topics = subscriptions | {channel_name}
        self._consumer.subscribe(list(new_topics))

    async def unsubscribe(self, channel_name: str) -> None:
        """Unsubscribe from a Kafka topic.

        Args:
            channel_name: The Kafka topic to unsubscribe from

        Note:
            Channel names with '/' are converted to '.' as Kafka topics
            don't support '/' characters.
        """
        channel_name = channel_name.replace("/", ".")
        subscriptions = self._consumer.subscription()
        new_topics = subscriptions - {channel_name}
        self._consumer.unsubscribe(list(new_topics))

    async def publish(self, channel_name: str, message: str) -> None:
        """Publish a message to a Kafka topic.

        Args:
            channel_name: The Kafka topic to publish to
            message: The message to publish (as a JSON string)

        Note:
            Channel names with '/' are converted to '.' as Kafka topics
            don't support '/' characters.
            The producer is started automatically on first publish if not already started.
        """
        channel_name = channel_name.replace("/", ".")
        if not self._is_producer_started:
            await self._producer.start()
            self._is_producer_started = True
        await self._producer.send(channel_name, message.encode("utf"))

    async def close(self) -> None:
        """Close the Kafka connections and clean up resources."""
        await self._producer.stop()
        await self._consumer.stop()

    async def read_messages(self) -> AsyncGenerator[BrokerMessage, None]:
        """Read messages from the Kafka broker.

        Returns:
            An async generator that yields BrokerMessage objects.

        Yields:
            BrokerMessage: Messages received from subscribed topics.

        Note:
            The consumer is started automatically when this method is called.
        """
        await self._consumer.start()
        async for message in self._consumer:
            payload = json.loads(message.value.decode())
            yield BrokerMessage(**payload)
