from abc import ABC, abstractmethod
from typing import AsyncGenerator

from pubsubbud.models import BrokerMessage, BrokerMessageHeader


class BrokerInterface(ABC):
    """Abstract base class defining the interface for message broker implementations.

    This interface defines the core functionality required for any message broker implementation
    in the pubsub system. Concrete implementations must provide these methods to handle
    message publishing, subscription, and reading.

    The interface supports:
    - Channel subscription and unsubscription
    - Message publishing
    - Message reading through an async generator
    - Resource cleanup
    """

    @abstractmethod
    async def subscribe(self, channel_name: str) -> None:
        """Subscribe to a channel to receive messages.

        Args:
            channel_name: The name of the channel to subscribe to.
        """
        pass

    @abstractmethod
    async def unsubscribe(self, channel_name: str) -> None:
        """Unsubscribe from a channel to stop receiving messages.

        Args:
            channel_name: The name of the channel to unsubscribe from.
        """
        pass

    @abstractmethod
    async def publish(self, channel_name: str, message: str) -> None:
        """Publish a message to a channel.

        Args:
            channel_name: The name of the channel to publish to.
            message: The message to publish, as a JSON string.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the broker connection and clean up resources.

        This method should be called when the broker is no longer needed to ensure
        proper cleanup of resources and connections.
        """
        pass

    @abstractmethod
    async def read_messages(self) -> AsyncGenerator[BrokerMessage, None]:
        """Read messages from subscribed channels.

        Returns:
            An async generator that yields BrokerMessage objects.

        Yields:
            BrokerMessage: Messages received from subscribed channels.

        Note:
            This is a default implementation that yields a dummy message.
            Concrete implementations should override this method to provide
            actual message reading functionality.
        """
        header = BrokerMessageHeader(message_id="1", channel="dummy", origin_id="dummy")
        yield BrokerMessage(header=header, content={"dummy": 1})
