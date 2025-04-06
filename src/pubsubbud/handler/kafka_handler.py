import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord
from aiokafka.errors import KafkaConnectionError

from pubsubbud.config import KafkaHandlerConfig
from pubsubbud.handler.handler_interface import HandlerConnectionError, HandlerInterface
from pubsubbud.models import BrokerMessage


class KafkaHandler(HandlerInterface):
    def __init__(self, name: str, config: KafkaHandlerConfig, logger: logging.Logger):
        super().__init__(name=name, publish_callback=self._send, logger=logger)
        port = config.port
        host = config.host
        server = f"{host}:{port}"
        self._subscribe_topic = config.to_pubsub_topic.replace("/", ".")
        self._publish_topic = config.from_pubsub_topic.replace("/", ".")
        self._connection_retries = config.connection_retries
        self._consumer = AIOKafkaConsumer(bootstrap_servers=[server])
        self._producer = AIOKafkaProducer(bootstrap_servers=[server])
        self._is_producer_started = False

    async def _add_message_to_queue(self, message: ConsumerRecord) -> None:
        payload = json.loads(message.value.decode())
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
        try:
            if not self._is_producer_started:
                await self._producer.start()
                self._is_producer_started = True
            message = {"content": content, "header": header}
            topic = self._publish_topic + "." + handler_id
            await self._producer.send(topic, value=json.dumps(message).encode("utf"))
        except KafkaConnectionError:
            raise HandlerConnectionError(
                f"Kafka connection lost for handler {handler_id}"
            )

    async def _handle_connection_error(self, handler_id: str) -> bool:
        retries = self._connection_retries
        while retries > 0:
            try:
                await self._producer.start()
                self._is_producer_started = True
                return True
            except KafkaConnectionError:
                retries -= 1
                await asyncio.sleep(1)  # Wait before retry
                self._logger.warning(
                    f"Retrying Kafka connection {handler_id}, {retries} attempts left"
                )
        return False
