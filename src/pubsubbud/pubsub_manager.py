import asyncio
import http
import json
import logging
import uuid
from fnmatch import fnmatch
from itertools import chain
from typing import Any, Optional

from pubsubbud.broker.broker_interface import BrokerInterface
from pubsubbud.custom_types import PubsubCallback
from pubsubbud.exceptions import MessageValidationError
from pubsubbud.handler.handler_interface import HandlerInterface
from pubsubbud.helpers import create_header
from pubsubbud.models import BrokerMessage


class PubsubManager:
    """A manager class for handling pub/sub operations with message brokers.

    This class manages pub/sub operations including:
    - Channel subscription and unsubscription
    - Message publishing and receiving
    - Callback registration and execution
    - Handler management and message forwarding

    Attributes:
        _message_task: Task for reading messages from the broker
        _logger: Logger instance for logging operations
        _channels: List of active channels
        _callbacks: Dictionary mapping channel names to their callbacks
        _pattern_callbacks: Dictionary mapping pattern-based channel names to their callbacks
        _uuid: Unique identifier for this manager instance
        _broker: Broker interface instance
        _handlers: Dictionary mapping handler names to their instances
        _handler_tasks: Dictionary mapping handler names to their tasks
    """

    def __init__(
        self,
        broker: BrokerInterface,
        logger: logging.Logger,
    ) -> None:
        """Initialize the PubsubManager.

        Args:
            broker: Broker interface instance for message handling
            logger: Logger instance for logging operations
        """
        self._message_task: Optional[asyncio.Task] = None
        self._logger = logger
        self._channels: list[str] = []
        self._callbacks: dict[str, list[PubsubCallback]] = {}
        self._pattern_callbacks: dict[str, list[PubsubCallback]] = {}
        self._uuid = str(uuid.uuid4())
        self._broker = broker
        self._handlers: dict[str, HandlerInterface] = {}
        self._handler_tasks: dict[str, asyncio.Task] = {}

    async def _cleanup_channels(self) -> None:
        """Remove channels that no longer have any subscribers."""
        for channel_name in self._channels:
            if not self._has_subscribers(channel_name):
                self._logger.info(f"Removing channel {channel_name}.")
                await self._remove_channel(channel_name)

    async def _add_channel(self, channel_name: str) -> None:
        """Add a new channel to the subscription list.

        Args:
            channel_name: Name of the channel to add
        """
        self._logger.info(f"Adding channel {channel_name}")
        if channel_name not in self._channels:
            await self._broker.subscribe(channel_name)
            await self._broker.subscribe(f"{self._uuid}/{channel_name}")
            self._channels.append(channel_name)
            await self._restart_message_task()
        await self._cleanup_channels()

    async def _remove_channel(self, channel_name: str) -> None:
        """Remove a channel from the subscription list.

        Args:
            channel_name: Name of the channel to remove
        """
        if channel_name in self._channels:
            await self._broker.unsubscribe(channel_name)
            await self._broker.unsubscribe(f"{self._uuid}/{channel_name}")
            self._channels.remove(channel_name)
        await self._cleanup_channels()

    async def register_callback(
        self, channel_name: str, callback: PubsubCallback
    ) -> None:
        """Register a callback function for a channel.

        Args:
            channel_name: Name of the channel to register the callback for
            callback: Callback function to be executed when messages are received
        """
        if "*" in channel_name:
            try:
                self._pattern_callbacks[channel_name].append(callback)
            except KeyError:
                self._pattern_callbacks[channel_name] = [callback]
        else:
            try:
                self._callbacks[channel_name].append(callback)
            except KeyError:
                self._callbacks[channel_name] = [callback]
            await self._add_channel(channel_name)

    async def unregister_callback(
        self, channel_name: str, callback: Optional[PubsubCallback] = None
    ) -> None:
        """Unregister a callback function from a channel.

        Args:
            channel_name: Name of the channel to unregister the callback from
            callback: Optional specific callback to unregister. If None, all callbacks for the channel are removed.
        """
        try:
            if "*" in channel_name:
                # Handle pattern callbacks
                if callback:
                    self._pattern_callbacks[channel_name].remove(callback)
                    if not self._pattern_callbacks[channel_name]:
                        del self._pattern_callbacks[channel_name]
                else:
                    del self._pattern_callbacks[channel_name]
            else:
                # Handle exact match callbacks
                if callback:
                    self._callbacks[channel_name].remove(callback)
                    if not self._callbacks[channel_name]:
                        del self._callbacks[channel_name]
                else:
                    del self._callbacks[channel_name]
            await self._cleanup_channels()

        except KeyError:
            self._logger.warning(
                f"Unable to unregister callbacks to channel name {channel_name}."
            )

    async def _subscribe(
        self,
        channel_name: str,
        handler_name: Optional[str] = None,
        handler_id: Optional[str] = None,
    ) -> None:
        """Subscribe to a channel, optionally for a specific handler.

        Args:
            channel_name: Name of the channel to subscribe to
            handler_name: Optional name of the handler subscribing
            handler_id: Optional ID of the handler subscribing
        """
        if handler_id and handler_name:
            self._handlers[handler_name].subscribe(channel_name, handler_id)
        await self._add_channel(channel_name)

    async def _unsubscribe(
        self,
        channel_name: str,
        handler_name: Optional[str] = None,
        handler_id: Optional[str] = None,
    ) -> None:
        """Unsubscribe from a channel, optionally for a specific handler.

        Args:
            channel_name: Name of the channel to unsubscribe from
            handler_name: Optional name of the handler unsubscribing
            handler_id: Optional ID of the handler unsubscribing
        """
        if handler_name:
            self._handlers[handler_name].unsubscribe(channel_name, handler_id)
        else:
            for handler in self._handlers.values():
                handler.unsubscribe(channel_name, handler_id)
        if not self._has_subscribers(channel_name):
            await self._remove_channel(channel_name)

    def _has_subscribers(self, channel_name: str) -> bool:
        """Check if a channel has any subscribers.

        Args:
            channel_name: Name of the channel to check

        Returns:
            bool: True if the channel has subscribers, False otherwise
        """
        # Check exact matches
        if channel_name in self._callbacks.keys():
            return True

        # Check pattern matches
        for pattern in self._pattern_callbacks.keys():
            if fnmatch(channel_name, pattern):
                return True

        # Check handlers
        for handler in self._handlers.values():
            if handler.has_subscribers(channel_name):
                return True
        return False

    def _run_message_task(self) -> None:
        """Start the task for reading messages from the broker."""
        self._message_task = asyncio.create_task(self._read_messages())

    async def _restart_message_task(self) -> None:
        """Restart the message reading task."""
        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.exceptions.CancelledError:
                pass
            finally:
                self._message_task = asyncio.create_task(self._read_messages())

    async def _handle_subscription_message(
        self, message: BrokerMessage, handler_name: str, handler_id: str
    ) -> None:
        """Handle subscription-related messages from handlers.

        Args:
            message: The subscription message to handle
            handler_name: Name of the handler sending the message
            handler_id: ID of the handler sending the message
        """
        subscription_type = message.content["subscription_type"]
        subscription_channel = message.content["subscription_channel"]
        if subscription_type == "subscription":
            await self._subscribe(subscription_channel, handler_name, handler_id)
        elif subscription_type == "unsubscription":
            await self._unsubscribe(subscription_channel, handler_name, handler_id)
        else:
            raise ValueError(f"Subscription type not supported: {subscription_type}.")

    async def _handle_pubsub_message(
        self, message: BrokerMessage, origin_id: str = "pubsub"
    ) -> None:
        """Handle pub/sub messages from handlers.

        Args:
            message: The message to handle
            origin_id: ID of the message origin, defaults to "pubsub"
        """
        channel_name = message.header.channel
        internal = message.header.internal
        content = message.content
        await self.publish(channel_name, content, internal, origin_id)

    def _run_handler_tasks(self) -> None:
        """Start tasks for all registered handlers."""
        for handler in self._handlers.values():
            handler.run()
            self._handler_tasks[handler.name] = asyncio.create_task(
                self._get_handler_messages(handler)
            )

    async def _get_handler_messages(self, handler: HandlerInterface) -> None:
        """Process messages from a handler.

        Args:
            handler: The handler to process messages from
        """
        async for message in handler.message_iterator:  # type: ignore
            try:
                channel_name = message.header.channel
                handler_id = message.header.origin_id
                message_id = message.header.message_id
                self._logger.info(f"Message from handler {handler.name}: {message}")
                if channel_name == "subscription":
                    await self._handle_subscription_message(
                        message, handler.name, handler_id
                    )
                else:
                    await self._handle_pubsub_message(message, handler_id)
                ack_header = {
                    "ack_id": message_id,
                    "status_code": http.HTTPStatus.OK,
                }
            except MessageValidationError:
                ack_header = {
                    "ack_id": message_id,
                    "status_code": http.HTTPStatus.UNPROCESSABLE_ENTITY,
                }
            except Exception:
                ack_header = {
                    "ack_id": message_id,
                    "status_code": http.HTTPStatus.INTERNAL_SERVER_ERROR,
                }
            finally:
                await handler.publish(handler_id, {}, ack_header)

    def run(self) -> None:
        """Start the pub/sub manager by running message and handler tasks."""
        self._run_message_task()
        self._run_handler_tasks()

    def _get_pattern_callbacks(self, channel_name: str) -> list[PubsubCallback]:
        """Get all pattern-matching callbacks for a channel.

        Args:
            channel_name: Name of the channel to get callbacks for

        Returns:
            list[PubsubCallback]: List of matching callbacks
        """
        return list(
            chain.from_iterable(
                [
                    callback
                    for pattern, callback in self._pattern_callbacks.items()
                    if fnmatch(channel_name, pattern)
                ]
            )
        )

    async def _execute_callbacks(
        self, channel_name: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        """Execute all registered callbacks for a channel.

        Args:
            channel_name: Name of the channel to execute callbacks for
            content: Content of the message
            header: Header information of the message
        """
        try:
            callbacks = self._callbacks[channel_name]
        except KeyError:
            callbacks = []
        pattern_callbacks = self._get_pattern_callbacks(channel_name)
        callbacks += pattern_callbacks
        for callback in callbacks:
            try:
                await callback(content, header)
            except Exception:
                self._logger.warning("Error executing callback.", exc_info=True)

    async def _read_messages(self) -> None:
        """Read and process messages from the broker."""
        async for message in self._broker.read_messages():
            if message:
                header = message.header
                channel_name = header.channel
                content = message.content
                self._logger.info(f"Message from broker: {message}")
                await self.forward_to_handlers(channel_name, content, header)
                if "/" in channel_name:
                    channel_name = channel_name.split("/")[1]
                await self._execute_callbacks(channel_name, content, header.dict())

    async def forward_to_handlers(
        self,
        channel: str,
        content: dict[str, Any],
        header: Any,
        handler_id: Optional[str] = None,
        handler_type: Optional[str] = None,
    ) -> None:
        """Forward a message to appropriate handlers.

        Args:
            channel: Channel name the message is from
            content: Content of the message
            header: Header information of the message
            handler_id: Optional specific handler ID to forward to
            handler_type: Optional specific handler type to forward to
        """
        if not handler_id and not handler_type:
            for handler in self._handlers.values():
                await handler.publish_if_subscribed(channel, content, header.dict())
        elif handler_id and handler_type:
            try:
                await self._handlers[handler_type].publish(
                    handler_id=handler_id, content=content, header=header
                )
            except KeyError:
                self._logger.warning(
                    f"Unable to forward to handler {handler_type} with id {handler_id}. Handler not found."
                )
        else:
            self._logger.warning(
                f"Unable to foward to handler for handler id {handler_id} and handler type {handler_type}. Both must be set to forward to a specific client."
            )

    def add_handler(self, handler: HandlerInterface) -> None:
        """Add a new handler to the manager.

        Args:
            handler: The handler to add
        """
        self._handlers[handler.name] = handler

    async def close(self) -> None:
        """Close the pub/sub manager and clean up resources."""
        self._logger.info("Closing pubsub.")
        if self._message_task:
            self._message_task.cancel()
        for task in self._handler_tasks.values():
            task.cancel()
        for handler in self._handlers.values():
            await handler.stop()
        await self._broker.close()

    async def publish(
        self,
        channel_name: str,
        data: dict[str, Any],
        internal: bool = False,
        origin_id: Optional[str] = None,
    ) -> None:
        """Publish a message to a channel.

        Args:
            channel_name: Name of the channel to publish to
            data: Data to publish
            internal: Whether this is an internal message
            origin_id: ID of the message origin, defaults to "pubsub"
        """
        if not origin_id:
            origin_id = self._uuid
        message = {}
        message["content"] = data
        message["header"] = create_header(channel_name, origin_id)
        if internal:
            channel_name = f"{self._uuid}/{channel_name}"
        self._logger.info(f"Message to broker: {message}, {channel_name}")
        await self._broker.publish(channel_name, json.dumps(message))
