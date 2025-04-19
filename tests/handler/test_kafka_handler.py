import asyncio
import json
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


@pytest.mark.asyncio
async def test_kafka_message_handling(kafka_handler):
    # Test message handling
    mock_message = MagicMock()
    mock_message.value = json.dumps(
        {
            "content": {"data": "test"},
            "header": {
                "message_id": "msg1",
                "channel": "test_channel",
                "type": "test",
                "origin_id": "test_client",
            },
        }
    ).encode()

    await kafka_handler._add_message_to_queue(mock_message)

    # Verify message was added to queue
    queued_message = await kafka_handler._message_queue.get()
    assert queued_message.content == {"data": "test"}
    assert queued_message.header.message_id == "msg1"
    assert queued_message.header.channel == "test_channel"
    assert queued_message.header.origin_id == "test_client"


@pytest.mark.asyncio
async def test_kafka_send_message(kafka_handler):
    # Test sending message when producer not started
    assert not kafka_handler._is_producer_started

    await kafka_handler._send(
        "client1", {"data": "test"}, {"message_id": "msg1", "origin_id": "test_client"}
    )

    # Verify producer was started
    assert kafka_handler._is_producer_started
    kafka_handler._producer.start.assert_called_once()

    # Verify message was sent
    kafka_handler._producer.send.assert_called_with(
        "test_out.client1",
        value=json.dumps(
            {
                "content": {"data": "test"},
                "header": {"message_id": "msg1", "origin_id": "test_client"},
            }
        ).encode("utf"),
    )

    # Test connection error
    kafka_handler._producer.send.side_effect = KafkaConnectionError()
    with pytest.raises(HandlerConnectionError) as exc_info:
        await kafka_handler._send("client1", {"data": "test"}, {"message_id": "msg1"})
    assert "Kafka connection lost for handler client1" in str(exc_info.value)


@pytest.mark.asyncio
async def test_kafka_read_messages(kafka_handler):
    # Mock consumer to return test messages
    mock_message1 = MagicMock()
    mock_message1.value = json.dumps(
        {
            "content": {"data": "test1"},
            "header": {
                "message_id": "msg1",
                "channel": "test_channel",
                "type": "test",
                "origin_id": "client1",
            },
        }
    ).encode()

    mock_message2 = MagicMock()
    mock_message2.value = json.dumps(
        {
            "content": {"data": "test2"},
            "header": {
                "message_id": "msg2",
                "channel": "test_channel",
                "type": "test",
                "origin_id": "client2",
            },
        }
    ).encode()

    # Set up consumer to yield our test messages
    kafka_handler._consumer.__aiter__.return_value = [mock_message1, mock_message2]

    # Make subscribe a regular MagicMock since it's not async
    kafka_handler._consumer.subscribe = MagicMock()
    # Keep start as AsyncMock since it is async
    kafka_handler._consumer.start = AsyncMock()

    # Start reading messages
    read_task = asyncio.create_task(kafka_handler._read_messages())

    # Wait for messages to be processed
    await asyncio.sleep(0.1)

    # Cancel the read task
    read_task.cancel()
    try:
        await read_task
    except asyncio.CancelledError:
        pass

    # Verify consumer was started and subscribed
    kafka_handler._consumer.start.assert_awaited_once()
    kafka_handler._consumer.subscribe.assert_called_with(
        ["test_in"]
    )  # regular mock assertion

    # Verify messages were processed
    message1 = await kafka_handler._message_queue.get()
    assert message1.content == {"data": "test1"}
    assert message1.header.message_id == "msg1"

    message2 = await kafka_handler._message_queue.get()
    assert message2.content == {"data": "test2"}
    assert message2.header.message_id == "msg2"


@pytest.mark.asyncio
async def test_kafka_stop(kafka_handler):
    # Start the handler
    kafka_handler.run()
    assert kafka_handler._run_task is not None

    # Stop the handler
    await kafka_handler.stop()

    # Verify consumer was stopped
    kafka_handler._consumer.stop.assert_called_once()
    assert kafka_handler._run_task.cancelled()
