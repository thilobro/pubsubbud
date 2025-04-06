from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from aiokafka.errors import KafkaConnectionError

from pubsubbud.config import KafkaHandlerConfig
from pubsubbud.handler.handler_interface import HandlerConnectionError
from pubsubbud.handler.kafka_handler import KafkaHandler


@pytest_asyncio.fixture
async def kafka_handler():
    logger = MagicMock()
    config = KafkaHandlerConfig(
        host="localhost",
        port=9092,
        to_pubsub_topic="test_in",
        from_pubsub_topic="test_out",
        connection_retries=2,
    )

    with (
        patch("aiokafka.AIOKafkaProducer") as mock_producer,
        patch("aiokafka.AIOKafkaConsumer") as mock_consumer,
    ):
        handler = KafkaHandler("test", config, logger)
        handler._producer = AsyncMock()
        handler._consumer = AsyncMock()
        handler._run_task = None  # Initialize the task
        yield handler
        await handler.stop()


@pytest.mark.asyncio
async def test_kafka_handler_connection_error(kafka_handler, monkeypatch):
    # Mock asyncio.sleep to return immediately
    async def mock_sleep(_):
        return

    monkeypatch.setattr("asyncio.sleep", mock_sleep)

    # Mock producer for testing retries
    kafka_handler._producer.start.side_effect = [
        KafkaConnectionError(),  # First attempt fails
        None,  # Second attempt succeeds
    ]

    # Test successful recovery after one retry
    assert await kafka_handler._handle_connection_error("test_id") is True
    assert kafka_handler._producer.start.call_count == 2

    # Reset mock and test complete failure
    kafka_handler._producer.start.reset_mock()
    kafka_handler._producer.start.side_effect = KafkaConnectionError()

    assert await kafka_handler._handle_connection_error("test_id") is False
    assert kafka_handler._producer.start.call_count == 2


@pytest.mark.asyncio
async def test_kafka_handler_publish_retry(kafka_handler):
    # Mock the publish_callback instead of _send
    kafka_handler._publish_callback = AsyncMock()
    kafka_handler._publish_callback.side_effect = [
        HandlerConnectionError(),  # First attempt fails
        None,  # Second attempt succeeds
    ]

    kafka_handler._handle_connection_error = AsyncMock(return_value=True)

    await kafka_handler.publish("test_id", {}, {})
    assert kafka_handler._publish_callback.call_count == 2
    assert kafka_handler._handle_connection_error.call_count == 1
