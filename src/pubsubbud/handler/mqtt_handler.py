import asyncio
import json
import logging
from typing import Any, Optional

from aiomqtt import Client

from pubsubbud.config import MqttHandlerConfig
from pubsubbud.handler.handler_interface import HandlerInterface
from pubsubbud.models import BrokerMessage


# TODO: move to paho mqtt!
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
        self._client = Client(hostname=config.host, port=config.port)
        self._run_task: Optional[asyncio.Task] = None

    async def _serve(self) -> None:
        async with self._client as client:
            await client.subscribe(self._subscribe_topic)
            async for message in client.messages:
                if isinstance(message.payload, bytes):
                    await self._message_queue.put(
                        {
                            "message": BrokerMessage(
                                **json.loads(message.payload.decode())
                            ),
                            "interface_id": self._subscribe_topic,
                        }
                    )
                    self._logger.info(
                        f"Put mqtt message {message.payload.decode()} into queue."
                    )

    def run(self) -> None:
        self._run_task = asyncio.create_task(self._serve())

    async def stop(self) -> None:
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.exceptions.CancelledError:
                pass
            self._logger.info(f"Interface {self._name} stopped.")

    async def _send(
        self, interface_id: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        message = {"content": content, "header": header}
        await self._client.publish(self._publish_topic, payload=json.dumps(message))
