import asyncio
import logging
from typing import Any

from pubsubbud.broker.kafka_broker import KafkaBroker
from pubsubbud.broker.mqtt_broker import MqttBroker
from pubsubbud.broker.redis_broker import RedisBroker
from pubsubbud.config import (
    KafkaBrokerConfig,
    MqttBrokerConfig,
    MqttHandlerConfig,
    PubsubManagerConfig,
    RedisBrokerConfig,
    WebsocketHandlerConfig,
)
from pubsubbud.handler import mqtt_handler, websocket_handler
from pubsubbud.pubsub_manager import PubsubManager

BROKER_TYPE = "kafka"


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
    if BROKER_TYPE == "redis":
        redis_broker_config_path = "./configs/redis_broker.json"
        config = RedisBrokerConfig.from_json(redis_broker_config_path)
        broker = RedisBroker(config)
    elif BROKER_TYPE == "mqtt":
        mqtt_broker_config_path = "./configs/mqtt_broker.json"
        config = MqttBrokerConfig.from_json(mqtt_broker_config_path)
        broker = MqttBroker(config)
    elif BROKER_TYPE == "kafka":
        kafka_broker_config_path = "./configs/kafka_broker.json"
        config = KafkaBrokerConfig.from_json(kafka_broker_config_path)
        broker = KafkaBroker(config)
    else:
        raise ValueError("Invalid broker specified")
    ps_manager_config = PubsubManagerConfig.from_json(pubsub_handler_config_path)
    ps_manager = PubsubManager(ps_manager_config, broker, logger)

    await ps_manager.register_callback("test", callback)
    await ps_manager.register_callback("test", callback2)

    websocket_handler_config_path = "./configs/websocket_handler.json"
    ws_handler_config = WebsocketHandlerConfig.from_json(websocket_handler_config_path)
    ws_handler = websocket_handler.WebsocketHandler(
        "websocket",
        ws_handler_config,
        logger,
    )
    mqtt_handler_config_path = "./configs/mqtt_handler.json"
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
