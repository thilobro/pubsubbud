import json
from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_redis_subscribe_unsubscribe(redis_broker):
    await redis_broker.subscribe("test_channel")
    redis_broker._broker.subscribe.assert_awaited_once_with("test_channel")


@pytest.mark.asyncio
async def test_redis_publish(redis_broker):
    message = {"test": "data"}
    await redis_broker.publish("test_channel", json.dumps(message))
    redis_broker._redis.publish.assert_called_once_with(
        "test_channel",
        json.dumps(message),
    )


@pytest.mark.asyncio
async def test_redis_read_messages(redis_broker):
    message_data = {
        "header": {
            "message_id": "test_id",
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
        "content": {"test": "data"},
    }
    test_message = {
        "type": "message",
        "data": json.dumps(message_data).encode(),
    }

    class AsyncIteratorMock:
        def __init__(self, items):
            self.items = items

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return self.items.pop(0)
            except IndexError:
                raise StopAsyncIteration

    redis_broker._broker.listen = MagicMock(
        return_value=AsyncIteratorMock([test_message])
    )

    async for message in redis_broker.read_messages():
        assert message.content == {"test": "data"}
        assert message.header.channel == "test_channel"
        break
