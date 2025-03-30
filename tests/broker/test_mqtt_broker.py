import json
from unittest.mock import MagicMock

import pytest

from pubsubbud.models import BrokerMessage


@pytest.mark.asyncio
async def test_mqtt_subscribe_unsubscribe(mqtt_broker):
    await mqtt_broker.subscribe("test/topic")
    mqtt_broker._client.subscribe.assert_called_once_with("test/topic")

    await mqtt_broker.unsubscribe("test/topic")
    mqtt_broker._client.unsubscribe.assert_called_once_with("test/topic")


@pytest.mark.asyncio
async def test_mqtt_publish(mqtt_broker):
    message = {"test": "data"}
    await mqtt_broker.publish("test/topic", json.dumps(message))
    mqtt_broker._client.publish.assert_called_once_with(
        "test/topic",
        json.dumps(message),
    )


@pytest.mark.asyncio
async def test_mqtt_message_handling(mqtt_broker):
    message_data = {
        "header": {
            "message_id": "test_id",
            "channel": "test/topic",
            "origin_id": "test_origin",
        },
        "content": {"test": "data"},
    }

    # Create a mock MQTT message
    mock_message = MagicMock()
    mock_message.payload = json.dumps(message_data).encode()

    # Put the mock message in the queue
    await mqtt_broker._message_queue.put(mock_message)

    # Use read_messages to get the processed BrokerMessage
    async for message in mqtt_broker.read_messages():
        assert isinstance(message, BrokerMessage)
        assert message.content == {"test": "data"}
        assert message.header.channel == "test/topic"
        break  # Exit after first message


@pytest.mark.asyncio
async def test_mqtt_close(mqtt_broker):
    await mqtt_broker.close()
    mqtt_broker._client.loop_stop.assert_called_once()
