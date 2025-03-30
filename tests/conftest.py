import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from pubsubbud.broker.kafka_broker import KafkaBroker
from pubsubbud.broker.mqtt_broker import MqttBroker
from pubsubbud.broker.redis_broker import RedisBroker
from pubsubbud.config import (
    KafkaBrokerConfig,
    MqttBrokerConfig,
    PubsubManagerConfig,
    RedisBrokerConfig,
    WebsocketHandlerConfig,
)
from pubsubbud.handler.websocket_handler import WebsocketHandler
from pubsubbud.pubsub_manager import PubsubManager


class AsyncContextManager(MagicMock):
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, traceback):
        pass


@pytest.fixture
def redis_broker_config():
    return RedisBrokerConfig(host="localhost", port=6379)


@pytest.fixture
def kafka_broker_config():
    return KafkaBrokerConfig(host="localhost", port=9092)


@pytest.fixture
def mqtt_broker_config():
    return MqttBrokerConfig(host="localhost", port=1883)


@pytest_asyncio.fixture
async def kafka_broker(kafka_broker_config):
    with (
        patch("aiokafka.AIOKafkaConsumer") as mock_consumer,
        patch("aiokafka.AIOKafkaProducer") as mock_producer,
    ):
        consumer = MagicMock()
        consumer.subscribe = MagicMock()  # sync method
        consumer.subscription = MagicMock(return_value=set())
        consumer.start = AsyncMock()
        consumer.stop = AsyncMock()
        mock_consumer.return_value = consumer

        producer = MagicMock()
        producer.start = AsyncMock()
        producer.stop = AsyncMock()
        producer.send = AsyncMock()
        mock_producer.return_value = producer

        broker = KafkaBroker(kafka_broker_config)
        broker._consumer = consumer
        broker._producer = producer
        return broker  # Return the broker directly, not as an async generator


@pytest.fixture
def test_websocket_handler(test_logger):
    config = WebsocketHandlerConfig(host="localhost", port=8675)
    return WebsocketHandler("websocket", config, test_logger)


@pytest.fixture
def test_pubsub_manager(test_logger):
    test_broker = None
    ps_manager = PubsubManager(
        config=PubsubManagerConfig(uuid="123"), broker=test_broker, logger=test_logger
    )
    ps_manager._broker = AsyncMock()
    ps_manager._broker.read_messages = AsyncContextManager()
    return ps_manager


@pytest.fixture
def test_logger():
    return logging.getLogger("test_logger")


@pytest_asyncio.fixture
async def mqtt_broker(mqtt_broker_config):
    with patch("paho.mqtt.client.Client") as mock_client:
        client = MagicMock()
        client.connect = MagicMock()
        client.loop_start = MagicMock()
        client.loop_stop = MagicMock()
        client.subscribe = MagicMock()
        client.unsubscribe = MagicMock()
        client.publish = MagicMock()
        mock_client.return_value = client

        broker = MqttBroker(mqtt_broker_config)
        broker._client = client
        broker._message_queue = asyncio.Queue()
        return broker


@pytest_asyncio.fixture
async def redis_broker(redis_broker_config):
    with patch("redis.asyncio.Redis") as mock_redis:
        redis_instance = AsyncMock()
        pubsub = AsyncMock()

        pubsub.subscribe = AsyncMock()
        pubsub.unsubscribe = AsyncMock()
        redis_instance.publish = AsyncMock()
        redis_instance.pubsub = MagicMock(return_value=pubsub)
        mock_redis.return_value = redis_instance

        broker = RedisBroker(redis_broker_config)
        broker._redis = redis_instance
        broker._broker = pubsub
        return broker
