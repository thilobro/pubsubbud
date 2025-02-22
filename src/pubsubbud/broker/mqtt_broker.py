import asyncio
import json
from typing import AsyncGenerator

import paho.mqtt.client as mqtt

from pubsubbud.broker.broker_interface import BrokerInterface
from pubsubbud.helpers import create_header
from pubsubbud.models import BrokerMessage


class MqttBroker(BrokerInterface):
    def __init__(self) -> None:
        self._message_queue: asyncio.Queue[mqtt.MQTTMessage] = asyncio.Queue()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_message = self._on_message
        self._client.connect("localhost", port=1883)
        self._client.loop_start()

    def _on_message(self, client, userdata, message) -> None:
        asyncio.run(self._add_message_to_queue(message))

    async def _add_message_to_queue(self, message) -> None:
        await self._message_queue.put(message)

    async def subscribe(self, channel_name: str) -> None:
        self._client.subscribe(channel_name)

    async def unsubscribe(self, channel_name: str) -> None:
        self._client.unsubscribe(channel_name)

    async def publish(self, channel_name: str, message: str) -> None:
        self._client.publish(channel_name, json.dumps(message))

    async def close(self) -> None:
        self._client.loop_stop()

    async def read_messages(self) -> AsyncGenerator[BrokerMessage, None]:
        while True:
            message = await self._message_queue.get()
            payload = json.loads(json.loads(message.payload.decode()))
            yield BrokerMessage(**payload)
