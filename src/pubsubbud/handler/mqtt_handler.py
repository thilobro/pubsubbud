import asyncio
import json
import logging
from typing import Any, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTT_ERR_NO_CONN, MQTT_ERR_QUEUE_SIZE

from pubsubbud.config import MqttHandlerConfig
from pubsubbud.handler.handler_interface import HandlerConnectionError, HandlerInterface
from pubsubbud.models import BrokerMessage


class MqttHandler(HandlerInterface):
    """MQTT implementation of the handler interface.

    This class implements the HandlerInterface using MQTT as the underlying
    communication protocol. It manages MQTT client connections and handles
    message routing between MQTT clients and the pubsub system.

    Attributes:
        _host: MQTT broker host address
        _port: MQTT broker port
        _to_pubsub_topic: Base topic for incoming messages
        _from_pubsub_topic: Base topic for outgoing messages
        _client: Paho MQTT client instance
        _run_task: Background task running the MQTT client loop
    """

    def __init__(
        self,
        name: str,
        config: MqttHandlerConfig,
        logger: logging.Logger,
    ) -> None:
        """Initialize the MQTT handler.

        Args:
            name: Name of the handler instance
            config: Configuration for the MQTT handler
            logger: Logger instance for logging operations
        """
        self._publish_callback = self._send  # Define callback before super().__init__
        super().__init__(name, self._publish_callback, logger)
        self._host = config.host  # Store host from config
        self._port = config.port  # Store port from config
        self._to_pubsub_topic = config.to_pubsub_topic
        self._from_pubsub_topic = config.from_pubsub_topic
        self._client = mqtt.Client()
        self._client.on_message = self._on_message
        self._client.connect(self._host, port=self._port)
        self._run_task: Optional[asyncio.Task] = None

    def _on_message(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ) -> None:
        """Callback for handling incoming MQTT messages.

        Args:
            client: The MQTT client instance
            userdata: User data passed to the client
            message: The received MQTT message
        """
        asyncio.run(self._add_message_to_queue(message))

    async def _add_message_to_queue(self, message: mqtt.MQTTMessage) -> None:
        """Add a received MQTT message to the internal queue.

        Args:
            message: The MQTT message to add to the queue
        """
        if isinstance(message.payload, bytes):
            try:
                payload = json.loads(message.payload.decode())
                try:
                    await self._message_queue.put(BrokerMessage(**payload))
                except (TypeError, KeyError) as e:
                    self._logger.warning(f"Invalid message format: {str(e)}")
            except json.JSONDecodeError:
                self._logger.warning("Invalid JSON payload received")

    def run(self) -> None:
        """Start the MQTT client and subscribe to the base topic."""
        self._client.subscribe(self._to_pubsub_topic)
        self._client.loop_start()

    async def stop(self) -> None:
        """Stop the MQTT client and clean up resources."""
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.exceptions.CancelledError:
                pass
            self._logger.info(f"Interface {self._name} stopped.")

    async def _send(
        self, handler_id: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        """Send a message to a specific MQTT client.

        Args:
            handler_id: ID of the MQTT client to send to
            content: Message content
            header: Message header

        Raises:
            HandlerConnectionError: If there is an MQTT connection error
        """
        message = {"content": content, "header": header}
        topic = self._from_pubsub_topic + "/" + handler_id
        result = self._client.publish(topic, payload=json.dumps(message))
        if result.rc in (MQTT_ERR_NO_CONN, MQTT_ERR_QUEUE_SIZE):
            raise HandlerConnectionError(
                f"MQTT connection error for handler {handler_id}"
            )

    def subscribe(self, channel_name: str, handler_id: str) -> None:
        """Subscribe a client to a channel and set up MQTT subscription.

        Args:
            channel_name: Name of the channel to subscribe to
            handler_id: ID of the client subscribing
        """
        super().subscribe(channel_name, handler_id)
        topic = self._to_pubsub_topic + "/" + handler_id
        self._client.subscribe(topic)

    def unsubscribe(
        self, channel_name: Optional[str] = None, handler_id: Optional[str] = None
    ) -> None:
        """Unsubscribe a client from a channel and clean up MQTT subscriptions.

        Args:
            channel_name: Optional name of the channel to unsubscribe from
            handler_id: Optional ID of the client to unsubscribe
        """
        if channel_name and not handler_id:
            # Unsubscribe all clients from the channel
            try:
                for h_id in self._subscribed_channels[channel_name]:
                    topic = self._to_pubsub_topic + "/" + h_id
                    self._client.unsubscribe(topic)
            except KeyError:
                self._logger.warning(
                    f"Attempted to unsubscribe from non-existent channel: {channel_name}"
                )
        elif handler_id:
            # Unsubscribe specific client from specific channel
            topic = self._to_pubsub_topic + "/" + handler_id
            self._client.unsubscribe(topic)

        # Call super().unsubscribe after MQTT operations to maintain internal state
        super().unsubscribe(channel_name, handler_id)

    async def _handle_connection_error(self, handler_id: str) -> bool:
        """Handle a connection error for an MQTT client.

        Args:
            handler_id: ID of the client that encountered the error

        Returns:
            bool: True if the connection was successfully reestablished,
                  False otherwise
        """
        try:
            self._client.connect(self._host, port=self._port)
            return True
        except ConnectionRefusedError:
            self._logger.warning(
                f"Connection error in handler {self._name} with id {handler_id}. "
                "No recovery attempted."
            )
            return False
