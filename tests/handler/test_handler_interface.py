import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from pubsubbud.config import KafkaHandlerConfig
from pubsubbud.exceptions import MessageValidationError
from pubsubbud.handler.handler_interface import HandlerConnectionError
from pubsubbud.handler.kafka_handler import KafkaHandler
from pubsubbud.models import BrokerMessage


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


@pytest.mark.asyncio
async def test_validation_success(test_handler):
    """Test successful message validation."""

    # Setup validation callback
    def validation_callback(content: dict) -> bool:
        return "valid" in content

    test_handler._content_validation_callback = validation_callback

    # Create a valid message
    message = BrokerMessage(
        channel="test_channel",
        content={"valid": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )

    # Test validation
    test_handler._validate_message(message)  # Should not raise


@pytest.mark.asyncio
async def test_validation_failure(test_handler):
    """Test failed message validation."""

    # Setup validation callback
    def validation_callback(content: dict) -> bool:
        return "valid" in content

    test_handler._content_validation_callback = validation_callback

    # Create an invalid message
    message = BrokerMessage(
        channel="test_channel",
        content={"invalid": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )

    # Test validation
    with pytest.raises(MessageValidationError):
        test_handler._validate_message(message)


@pytest.mark.asyncio
async def test_validation_no_callback(test_handler):
    """Test message validation when no callback is set."""
    # Create a message
    message = BrokerMessage(
        channel="test_channel",
        content={"test": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )

    # Test validation (should pass as no callback is set)
    test_handler._validate_message(message)  # Should not raise


@pytest.mark.asyncio
async def test_validation_in_message_queue(test_handler):
    """Test validation in message queue processing."""

    # Setup validation callback
    def validation_callback(content: dict) -> bool:
        return "valid" in content

    test_handler._content_validation_callback = validation_callback

    # Create messages
    valid_message = BrokerMessage(
        channel="test_channel",
        content={"valid": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )
    invalid_message = BrokerMessage(
        channel="test_channel",
        content={"invalid": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )

    # Add messages to queue
    await test_handler._message_queue.put(valid_message)
    await test_handler._message_queue.put(invalid_message)

    # Test message queue processing
    async for message in test_handler.message_iterator:
        assert message == valid_message
        break  # Only process the first message

    # Verify invalid message was not processed
    assert not test_handler._message_queue.empty()
