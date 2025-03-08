import asyncio
import logging
import os

from pubsubbud.broker.redis_broker import RedisBroker
from pubsubbud.config import (
    PubsubManagerConfig,
    RedisBrokerConfig,
    WebsocketHandlerConfig,
)
from pubsubbud.handler import websocket_handler
from pubsubbud.pubsub_manager import PubsubManager

BROKER = os.environ.get("BROKER", "redis")


class CLIChatServer:
    def __init__(self, logger):
        self._logger = logger
        if BROKER == "redis":
            redis_broker_config_path = "./configs/redis_broker.json"
            config = RedisBrokerConfig.from_json(redis_broker_config_path)
            broker = RedisBroker(config)
        else:
            raise ValueError(f"Unknown broker: {BROKER}")
        pubsub_manager_config_path = "./configs/pubsub.json"
        ps_manager_config = PubsubManagerConfig.from_json(pubsub_manager_config_path)
        self._ps_manager = PubsubManager(ps_manager_config, broker, logger)

        websocket_handler_config_path = "./configs/websocket_handler.json"
        ws_handler_config = WebsocketHandlerConfig.from_json(
            websocket_handler_config_path
        )
        ws_handler = websocket_handler.WebsocketHandler(
            "websocket",
            ws_handler_config,
            logger,
        )

        self._ps_manager.add_handler(ws_handler)

    async def run(self):
        self._ps_manager.run()


async def main():
    logger = logging.getLogger("test_logger")
    logging.basicConfig(level=logging.INFO)
    chat_server = CLIChatServer(logger)
    await chat_server.run()
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
