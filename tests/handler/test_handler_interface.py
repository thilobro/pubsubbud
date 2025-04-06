from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from pubsubbud.config import KafkaHandlerConfig
from pubsubbud.handler.handler_interface import HandlerConnectionError
from pubsubbud.handler.kafka_handler import KafkaHandler


@pytest_asyncio.fixture
async def test_handler():
    logger = MagicMock()
    config = KafkaHandlerConfig(
        host="localhost",
        port=9092,
        to_pubsub_topic="test_in",
        from_pubsub_topic="test_out",
        connection_retries=1,
    )

    with patch("aiokafka.AIOKafkaProducer"), patch("aiokafka.AIOKafkaConsumer"):
        handler = KafkaHandler("test", config, logger)
        handler._producer = AsyncMock()
        handler._consumer = AsyncMock()
        handler._run_task = None  # Initialize the task
        yield handler
        await handler.stop()


@pytest.mark.asyncio
async def test_handler_interface_publish_retry(test_handler):
    # Mock the publish_callback instead of _send
    test_handler._publish_callback = AsyncMock()
    test_handler._publish_callback.side_effect = [
        HandlerConnectionError(),  # First attempt fails
        None,  # Second attempt succeeds
    ]

    test_handler._handle_connection_error = AsyncMock(return_value=True)

    await test_handler.publish("test_id", {}, {})
    assert test_handler._publish_callback.call_count == 2
    assert test_handler._handle_connection_error.call_count == 1

    # Test complete failure scenario
    test_handler._publish_callback.reset_mock()
    test_handler._handle_connection_error.reset_mock()
    test_handler._publish_callback.side_effect = HandlerConnectionError()
    test_handler._handle_connection_error.return_value = False

    await test_handler.publish("test_id", {}, {})
    assert test_handler._publish_callback.call_count == 1
    assert test_handler._handle_connection_error.call_count == 1
