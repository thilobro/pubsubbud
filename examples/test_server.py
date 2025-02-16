import asyncio
import logging
from typing import Any

from pubsubbud import pubsub_handler, websocket_handler
from pubsubbud.config import PubsubHandlerConfig, WebsocketHandlerConfig


async def callback(content: dict[str, Any], header: dict[str, Any]) -> None:
    print("Executed callback")
    print(content)
    print(header)


async def callback2(content: dict[str, Any], header: dict[str, Any]) -> None:
    print("Executed callback2")
    print(content)
    print(header)


async def main() -> None:
    logger = logging.getLogger("test_logger")

    pubsub_handler_config_path = "./configs/pubsub.json"
    ps_handler_config = PubsubHandlerConfig.from_json(pubsub_handler_config_path)
    ps_handler = pubsub_handler.PubsubHandler(ps_handler_config, logger)

    await ps_handler.register_callback("test", callback)
    await ps_handler.register_callback("test", callback2)

    websocket_handler_config_path = "./configs/websocket.json"
    ws_handler_config = WebsocketHandlerConfig.from_json(websocket_handler_config_path)
    ws_handler = websocket_handler.WebsocketHandler(
        "websocket",
        ws_handler_config,
        logger,
    )

    ps_handler.add_interface(ws_handler)
    await ps_handler.publish("test", {"test": 1})
    ps_handler.run()
    for i in range(10):
        await asyncio.sleep(5)
        await ps_handler.publish("test", {"test": 1})
    await ps_handler.close()


asyncio.run(main())
