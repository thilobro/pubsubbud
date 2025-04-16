import json
from typing import AsyncGenerator

import redis.asyncio as redis

from pubsubbud.broker.broker_interface import BrokerInterface
from pubsubbud.config import RedisBrokerConfig
from pubsubbud.models import BrokerMessage


class RedisBroker(BrokerInterface):
    """Redis implementation of the broker interface.

    This class implements the BrokerInterface using Redis as the underlying
    message broker. It uses the redis-py library for async communication.

    Attributes:
        _redis: Redis client instance
        _broker: Redis pubsub instance for handling subscriptions
    """

    def __init__(self, config: RedisBrokerConfig) -> None:
        """Initialize the Redis broker.

        Args:
            config: Configuration for the Redis broker connection
        """
        self._redis = redis.Redis(host=config.host, port=config.port)
        self._broker = self._redis.pubsub()

    async def subscribe(self, channel_name: str) -> None:
        """Subscribe to a Redis channel.

        Args:
            channel_name: The Redis channel to subscribe to
        """
        await self._broker.subscribe(channel_name)

    async def unsubscribe(self, channel_name: str) -> None:
        """Unsubscribe from a Redis channel.

        Args:
            channel_name: The Redis channel to unsubscribe from
        """
        await self._broker.unsubscribe(channel_name)

    async def publish(self, channel_name: str, message: str) -> None:
        """Publish a message to a Redis channel.

        Args:
            channel_name: The Redis channel to publish to
            message: The message to publish (as a JSON string)
        """
        await self._redis.publish(channel_name, message)

    async def close(self) -> None:
        """Close the Redis connection and clean up resources.

        Note:
            Currently, Redis connections are managed by the redis-py library
            and don't require explicit cleanup.
        """
        pass

    async def read_messages(self) -> AsyncGenerator[BrokerMessage, None]:
        """Read messages from the Redis broker.

        Returns:
            An async generator that yields BrokerMessage objects.

        Yields:
            BrokerMessage: Messages received from subscribed channels.

        Note:
            This method filters out Redis subscription messages and only
            yields actual message content.
        """
        async for message in self._broker.listen():
            if "subscribe" not in message["type"]:
                payload = json.loads(message["data"].decode())
                yield BrokerMessage(**payload)
