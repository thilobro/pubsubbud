import asyncio
import json
import logging
from typing import Any, Optional

import paho.mqtt.client as mqtt

from pubsubbud.config import MqttHandlerConfig
from pubsubbud.handler.handler_interface import HandlerInterface
from pubsubbud.models import BrokerMessage


class MqttHandler(HandlerInterface):
    def __init__(
        self,
        name: str,
        config: MqttHandlerConfig,
        logger: logging.Logger,
    ) -> None:
        super().__init__(name=name, publish_callback=self._send, logger=logger)
        self._subscribe_topic = config.to_pubsub_topic
        self._publish_topic = config.from_pubsub_topic
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_message = self._on_message
        self._client.connect("localhost", port=1883)
        self._run_task: Optional[asyncio.Task] = None

    def _on_message(self, client, userdata, message) -> None:
        asyncio.run(self._add_message_to_queue(message))

    async def _add_message_to_queue(self, message) -> None:
        if isinstance(message.payload, bytes):
            await self._message_queue.put(
                BrokerMessage(**json.loads(message.payload.decode()))
            )

    def run(self) -> None:
        self._client.subscribe(self._subscribe_topic)
        self._client.loop_start()

    async def stop(self) -> None:
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
        message = {"content": content, "header": header}
        topic = self._publish_topic + "/" + handler_id
        self._client.publish(topic, payload=json.dumps(message))

    def subscribe(self, channel_name: str, handler_id: str) -> None:
        super().subscribe(channel_name, handler_id)
        topic = self._subscribe_topic + "/" + handler_id
        self._client.subscribe(topic)

    def unsubscribe(
        self, channel_name: Optional[str] = None, handler_id: Optional[str] = None
    ) -> None:
        super().unsubscribe(channel_name, handler_id)
        if handler_id and channel_name:
            topic = self._subscribe_topic + "/" + handler_id
            if not self.has_subscribers(channel_name):
                self._client.unsubscribe(topic)
        elif handler_id:
            topic = self._subscribe_topic + "/" + handler_id
            self._client.unsubscribe(topic)
        elif channel_name:
            if not self.has_subscribers(channel_name):
                for handler_id in self._subscribed_channels[channel_name]:
                    topic = self._subscribe_topic + "/" + handler_id
                    self._client.unsubscribe(topic)
