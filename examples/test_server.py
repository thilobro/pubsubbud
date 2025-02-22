import asyncio
import logging
from typing import Any

from pubsubbud.broker.mqtt_broker import MqttBroker
from pubsubbud.broker.redis_broker import RedisBroker
from pubsubbud.config import (
    MqttHandlerConfig,
    PubsubManagerConfig,
    WebsocketHandlerConfig,
)
from pubsubbud.handler import mqtt_handler, websocket_handler
from pubsubbud.pubsub_manager import PubsubManager


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
    logging.basicConfig(level=logging.INFO)

    pubsub_handler_config_path = "./configs/pubsub.json"
    broker = RedisBroker()
    ps_manager_config = PubsubManagerConfig.from_json(pubsub_handler_config_path)
    ps_manager = PubsubManager(ps_manager_config, broker, logger)

    await ps_manager.register_callback("test", callback)
    await ps_manager.register_callback("test", callback2)

    websocket_handler_config_path = "./configs/websocket.json"
    ws_handler_config = WebsocketHandlerConfig.from_json(websocket_handler_config_path)
    ws_handler = websocket_handler.WebsocketHandler(
        "websocket",
        ws_handler_config,
        logger,
    )
    mqtt_handler_config_path = "./configs/mqtt.json"
    mqtt_handler_config = MqttHandlerConfig.from_json(mqtt_handler_config_path)
    m_handler = mqtt_handler.MqttHandler("mqtt", mqtt_handler_config, logger)

    ps_manager.add_handler(ws_handler)
    ps_manager.add_handler(m_handler)
    await ps_manager.publish("test", {"test": 1})
    ps_manager.run()
    for i in range(10):
        await asyncio.sleep(5)
        await ps_manager.publish("test", {"test": 1})
    await ps_manager.close()


asyncio.run(main())
