import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterable, Optional

from pubsubbud.custom_types import HandlerPublishCallback
from pubsubbud.models import BrokerMessage


class HandlerConnectionError(Exception):
    """Exception raised when a handler encounters a connection error."""

    pass


class HandlerInterface(ABC):
    """Abstract base class for message handlers in the pubsub system.

    This interface defines the core functionality required for any message handler
    implementation. Handlers manage client connections and message routing between

    clients and the pubsub system.

    Attributes:
        _name: Name of the handler instance
        _logger: Logger instance for logging operations
        _message_queue: Queue for incoming messages
        _publish_callback: Callback function for publishing messages
        _subscribed_channels: Dictionary mapping channels to their subscriber IDs
    """

    def __init__(
        self,
        name: str,
        publish_callback: HandlerPublishCallback,
        logger: logging.Logger,
    ) -> None:
        """Initialize the handler.

        Args:
            name: Name of the handler instance
            publish_callback: Callback function for publishing messages
            logger: Logger instance for logging operations
        """
        self._name = name
        self._logger = logger
        self._message_queue: asyncio.Queue[BrokerMessage] = asyncio.Queue(maxsize=100)
        self._publish_callback = publish_callback
        self._subscribed_channels: dict[str, list[str]] = {}

    def subscribe(self, channel_name: str, handler_id: str) -> None:
        """Subscribe a client to a channel.

        Args:
            channel_name: Name of the channel to subscribe to
            handler_id: ID of the client subscribing

        Note:
            If the client is already subscribed, the operation is ignored.
        """
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
        """Unsubscribe a client from a channel or all channels.

        Args:
            channel_name: Optional name of the channel to unsubscribe from
            handler_id: Optional ID of the client to unsubscribe

        Note:
            - If only channel_name is provided, all subscribers to that channel are removed
            - If both channel_name and handler_id are provided, only that specific subscription is removed
            - If only handler_id is provided, the client is unsubscribed from all channels
        """
        channels_to_remove = []
        if channel_name and not handler_id:
            try:
                del self._subscribed_channels[channel_name]
            except KeyError:
                self._logger.warning(
                    f"Attempted to unsubscribe from non-existent channel: {channel_name}"
                )
        elif channel_name and handler_id:
            try:
                self._subscribed_channels[channel_name].remove(handler_id)
            except KeyError:
                self._logger.warning(
                    f"Attempted to unsubscribe from non-existent channel: {channel_name}"
                )
                return
            except ValueError:
                self._logger.warning(
                    f"Attempted to unsubscribe from non-existent handler: {handler_id}"
                )
                return
            if not self.has_subscribers(channel_name):
                channels_to_remove.append(channel_name)
        else:  # only handler id
            for channel_name, handler_ids in self._subscribed_channels.items():
                if handler_id in handler_ids:
                    self._subscribed_channels[channel_name].remove(handler_id)
                    if not self.has_subscribers(channel_name):
                        channels_to_remove.append(channel_name)
        for channel_name in channels_to_remove:
            del self._subscribed_channels[channel_name]

    def has_subscribers(self, channel_name: str) -> bool:
        """Check if a channel has any subscribers.

        Args:
            channel_name: Name of the channel to check

        Returns:
            bool: True if the channel has subscribers, False otherwise
        """
        return (
            channel_name in self._subscribed_channels.keys()
            and self._subscribed_channels[channel_name] != []
        )

    async def publish(
        self, handler_id: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        """Publish a message to a specific client.

        Args:
            handler_id: ID of the client to publish to
            content: Message content
            header: Message header

        Note:
            If a connection error occurs, the handler will attempt to recover
            and retry the publish operation once.
        """
        try:
            await self._publish_callback(handler_id, content, header)
        except HandlerConnectionError:
            if await self._handle_connection_error(handler_id):
                # Retry if handler indicates recovery was successful
                await self._publish_callback(handler_id, content, header)
            else:
                self._logger.warning(
                    f"Handler {self._name} with id {handler_id} disconnected."
                )
                self.unsubscribe(handler_id=handler_id)

    async def publish_if_subscribed(
        self, channel_name: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        """Publish a message to all subscribers of a channel.

        Args:
            channel_name: Name of the channel to publish to
            content: Message content
            header: Message header
        """
        if self.has_subscribers(channel_name):
            handler_ids = self._subscribed_channels[channel_name]
            for handler_id in handler_ids:
                await self.publish(handler_id, content, header)

    async def _message_iterator(self) -> AsyncIterable:
        """Get an async iterator for incoming messages.

        Returns:
            AsyncIterable: An async iterator that yields messages from the queue
        """
        while True:
            message = await self._message_queue.get()
            yield message

    @abstractmethod
    async def stop(self) -> None:
        """Stop the handler and clean up resources.

        This method should be implemented by concrete handler classes to perform
        any necessary cleanup when the handler is being shut down.
        """
        pass

    @abstractmethod
    def run(self) -> None:
        """Start the handler.

        This method should be implemented by concrete handler classes to start
        the handler's main processing loop.
        """
        pass

    async def _handle_connection_error(self, handler_id: str) -> bool:
        """Handle a connection error for a client.

        Args:
            handler_id: ID of the client that encountered the error

        Returns:
            bool: True if the error was handled and the connection can be retried,
                  False otherwise

        Note:
            This base implementation logs the error and returns False. Concrete
            handlers should override this method to implement their own error
            handling logic.
        """
        self._logger.warning(
            f"Connection error in handler {self._name} with id {handler_id}. "
            "No recovery attempted."
        )
        return False

    @property
    def name(self) -> str:
        """Get the name of the handler.

        Returns:
            str: The handler's name
        """
        return self._name

    @property
    def message_iterator(self) -> Optional[AsyncIterable]:
        """Get the message iterator for this handler.

        Returns:
            Optional[AsyncIterable]: The message iterator, or None if not available
        """
        return self._message_iterator()
