import asyncio
import logging
from typing import Any

from pubsubbud import callback_handler, pubsub_handler, websocket_handler
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

    cb_handler = callback_handler.CallbackHandler(logger)
    cb_handler.register_callback("test_callback", callback)
    cb_handler.register_callback("test_callback", callback2)

    websocket_handler_config_path = "./configs/websocket.json"
    ws_handler_config = WebsocketHandlerConfig.from_json(websocket_handler_config_path)
    ws_handler = websocket_handler.WebsocketHandler(
        ps_handler.publish,
        ps_handler.subscribe,
        ps_handler.unsubscribe,
        ws_handler_config,
        logger,
    )

    ps_handler.add_interface("callback", cb_handler)
    ps_handler.add_interface("websocket", ws_handler)
    await ps_handler.subscribe(
        channel_name="test", interface_name="callback", interface_id="test_callback"
    )
    await ps_handler.publish("test", {"test": 1})
    ps_handler.run()
    while True:
        await asyncio.sleep(5)
        await ps_handler.publish("test", {"test": 1})
    # ps_handler.close()


asyncio.run(main())
