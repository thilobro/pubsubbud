import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from pubsubbud.config import KafkaHandlerConfig
from pubsubbud.handler.handler_interface import HandlerInterface
from pubsubbud.models import BrokerMessage


class KafkaHandler(HandlerInterface):
    def __init__(self, name: str, config: KafkaHandlerConfig, logger: logging.Logger):
        super().__init__(name=name, publish_callback=self._send, logger=logger)
        port = config.port
        host = config.host
        server = f"{host}:{port}"
        self._subscribe_topic = config.to_pubsub_topic.replace("/", ".")
        self._publish_topic = config.from_pubsub_topic.replace("/", ".")
        self._consumer = AIOKafkaConsumer(bootstrap_servers=[server])
        self._producer = AIOKafkaProducer(bootstrap_servers=[server])
        self._is_producer_started = False

    async def _add_message_to_queue(self, message) -> None:
        payload = json.loads(message.value.decode())
        import pdb

        pdb.set_trace()
        await self._message_queue.put(BrokerMessage(**payload))

    def run(self) -> None:
        self._run_task = asyncio.create_task(self._read_messages())

    async def stop(self) -> None:
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.exceptions.CancelledError:
                pass
        await self._consumer.stop()

    async def _read_messages(self) -> None:
        await self._consumer.start()
        self._consumer.subscribe([self._subscribe_topic])
        async for message in self._consumer:
            await self._add_message_to_queue(message)

    async def _send(
        self, handler_id: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        if not self._is_producer_started:
            await self._producer.start()
            self._is_producer_started = True
        message = {"content": content, "header": header}
        topic = self._publish_topic + "/" + handler_id
        self._producer.send(topic, value=json.dumps(message).encode("utf"))
