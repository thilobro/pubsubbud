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
