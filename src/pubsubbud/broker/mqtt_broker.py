import asyncio
import json
from typing import Any, AsyncGenerator

import paho.mqtt.client as mqtt

from pubsubbud.broker.broker_interface import BrokerInterface
from pubsubbud.config import MqttBrokerConfig
from pubsubbud.models import BrokerMessage


class MqttBroker(BrokerInterface):
    """MQTT implementation of the broker interface.

    This class implements the BrokerInterface using MQTT as the underlying
    message broker. It uses the Paho MQTT client library for communication.

    Attributes:
        _message_queue: Queue for storing incoming MQTT messages
        _client: Paho MQTT client instance
    """

    def __init__(self, config: MqttBrokerConfig) -> None:
        """Initialize the MQTT broker.

        Args:
            config: Configuration for the MQTT broker connection
        """
        self._message_queue: asyncio.Queue[mqtt.MQTTMessage] = asyncio.Queue()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_message = self._on_message
        self._client.connect(config.host, port=config.port)
        self._client.loop_start()

    def _on_message(
        self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage
    ) -> None:
        """Callback for handling incoming MQTT messages.

        This method is called by the Paho MQTT client when a message is received.
        It adds the message to the internal queue for processing.

        Args:
            client: The MQTT client instance
            userdata: User data passed to the client
            message: The received MQTT message
        """
        asyncio.run(self._add_message_to_queue(message))

    async def _add_message_to_queue(self, message: mqtt.MQTTMessage) -> None:
        """Add a received message to the internal queue.

        Args:
            message: The MQTT message to add to the queue
        """
        await self._message_queue.put(message)

    async def subscribe(self, channel_name: str) -> None:
        """Subscribe to an MQTT topic.

        Args:
            channel_name: The MQTT topic to subscribe to
        """
        self._client.subscribe(channel_name)

    async def unsubscribe(self, channel_name: str) -> None:
        """Unsubscribe from an MQTT topic.

        Args:
            channel_name: The MQTT topic to unsubscribe from
        """
        self._client.unsubscribe(channel_name)

    async def publish(self, channel_name: str, message: str) -> None:
        """Publish a message to an MQTT topic.

        Args:
            channel_name: The MQTT topic to publish to
            message: The message to publish (as a JSON string)
        """
        self._client.publish(channel_name, message)

    async def close(self) -> None:
        """Close the MQTT connection and clean up resources."""
        self._client.loop_stop()

    async def read_messages(self) -> AsyncGenerator[BrokerMessage, None]:
        """Read messages from the MQTT broker.

        Returns:
            An async generator that yields BrokerMessage objects.

        Yields:
            BrokerMessage: Messages received from subscribed topics.
        """
        while True:
            message = await self._message_queue.get()
            payload = json.loads(message.payload.decode())
            yield BrokerMessage(**payload)
