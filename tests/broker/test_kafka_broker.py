import json
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_kafka_subscribe_unsubscribe(kafka_broker):
    test_channel = "test/channel"
    expected_channel = "test.channel"

    kafka_broker._consumer.subscribe = MagicMock()
    kafka_broker._consumer.subscription = MagicMock(return_value=set())

    await kafka_broker.subscribe(test_channel)

    kafka_broker._consumer.subscribe.assert_called_once_with([expected_channel])


@pytest.mark.asyncio
async def test_kafka_publish(kafka_broker):
    message = {"test": "data"}
    await kafka_broker.publish("test/channel", json.dumps(message))
    kafka_broker._producer.send.assert_awaited_once_with(
        "test.channel",  # Note: "/" gets replaced with "."
        json.dumps(message).encode("utf"),
    )


@pytest.mark.asyncio
async def test_kafka_producer_starts_on_first_publish(kafka_broker):
    message = {"test": "data"}
    assert not kafka_broker._is_producer_started
    await kafka_broker.publish("test/channel", json.dumps(message))
    assert kafka_broker._is_producer_started
    kafka_broker._producer.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_kafka_close(kafka_broker):
    await kafka_broker.close()
    kafka_broker._producer.stop.assert_called_once()
    kafka_broker._consumer.stop.assert_called_once()


@pytest.mark.asyncio
async def test_kafka_read_messages(kafka_broker):
    message_data = {
        "header": {
            "message_id": "test_id",
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
        "content": {"test": "data"},
    }

    # Create a message with single encoding
    test_message = MagicMock()
    test_message.value = json.dumps(message_data).encode()

    # Set up the consumer mock
    consumer_mock = AsyncMock()
    # Set up the async iterator to return our test message
    consumer_mock.__aiter__.return_value.__anext__.side_effect = [
        test_message,
        StopAsyncIteration,
    ]
    kafka_broker._consumer = consumer_mock

    async for message in kafka_broker.read_messages():
        assert message.content == {"test": "data"}
        assert message.header.channel == "test_channel"
        break


@pytest.mark.asyncio
async def test_kafka_broker_error_handling(kafka_broker):
    """Test error handling in Kafka broker."""
    # Test producer error (lines 61-64)
    kafka_broker._producer.send.side_effect = Exception("Producer error")
    with pytest.raises(Exception):
        await kafka_broker.publish("test_channel", "test_message")

    # Test consumer error (lines 103-104)
    kafka_broker._consumer.start.side_effect = Exception("Consumer error")
    messages = []
    with pytest.raises(Exception, match="Consumer error"):
        async for message in kafka_broker.read_messages():
            messages.append(message)


@pytest.mark.asyncio
async def test_kafka_unsubscribe_behavior(kafka_broker):
    """Test unsubscribe behavior."""
    # Test unsubscribe with empty subscription
    kafka_broker._consumer.subscription = MagicMock(return_value=set())
    kafka_broker._consumer.unsubscribe = MagicMock()
    await kafka_broker.unsubscribe("test_channel")
    kafka_broker._consumer.unsubscribe.assert_called_once_with([])

    # Test unsubscribe with existing subscriptions
    kafka_broker._consumer.subscription = MagicMock(
        return_value={"channel1", "channel2", "test_channel"}
    )
    kafka_broker._consumer.unsubscribe.reset_mock()
    await kafka_broker.unsubscribe("test_channel")
    # Sort the list to make the test deterministic
    actual_call = kafka_broker._consumer.unsubscribe.call_args[0][0]
    assert sorted(actual_call) == ["channel1", "channel2"]


@pytest.mark.asyncio
async def test_kafka_channel_name_sanitization(kafka_broker):
    """Test channel name sanitization."""
    test_cases = [
        ("test/channel", "test.channel"),
        ("test/nested/channel", "test.nested.channel"),
        ("test.channel", "test.channel"),
        ("test-channel", "test-channel"),
    ]

    kafka_broker._consumer.subscribe = MagicMock()
    kafka_broker._consumer.subscription = MagicMock(return_value=set())
    kafka_broker._producer.send = AsyncMock()

    for input_name, expected_name in test_cases:
        # Test subscribe
        await kafka_broker.subscribe(input_name)
        kafka_broker._consumer.subscribe.assert_called_with([expected_name])
        kafka_broker._consumer.subscribe.reset_mock()

        # Test publish
        await kafka_broker.publish(input_name, "test_message")
        kafka_broker._producer.send.assert_awaited_with(
            expected_name, "test_message".encode("utf")
        )
        kafka_broker._producer.send.reset_mock()


@pytest.mark.asyncio
async def test_kafka_multiple_messages(kafka_broker):
    """Test reading multiple messages."""
    messages = [
        {
            "header": {
                "message_id": f"id_{i}",
                "channel": f"channel_{i}",
                "origin_id": f"origin_{i}",
                "type": "test",  # Add required type field
            },
            "content": {"data": f"test_{i}"},
        }
        for i in range(3)
    ]

    # Create mock messages
    mock_messages = []
    for msg_data in messages:
        mock_msg = MagicMock()
        mock_msg.value = json.dumps(msg_data).encode()
        mock_messages.append(mock_msg)

    # Set up consumer mock to return multiple messages
    consumer_mock = AsyncMock()
    consumer_mock.__aiter__.return_value = mock_messages
    kafka_broker._consumer = consumer_mock

    # Read all messages
    received_messages = []
    async for message in kafka_broker.read_messages():
        received_messages.append(message)
        if len(received_messages) == 3:
            break

    # Verify messages
    assert len(received_messages) == 3
    for i, msg in enumerate(received_messages):
        assert msg.header.message_id == f"id_{i}"
        assert msg.header.channel == f"channel_{i}"
        assert msg.content == {"data": f"test_{i}"}
