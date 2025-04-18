import json
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt
import pytest

from pubsubbud.config import MqttHandlerConfig
from pubsubbud.handler.handler_interface import HandlerConnectionError
from pubsubbud.handler.mqtt_handler import MqttHandler


@pytest.mark.asyncio
async def test_mqtt_handler_connection_error():
    with patch("paho.mqtt.client.Client") as mock_client_class:
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        logger = MagicMock()
        config = MqttHandlerConfig(
            host="localhost",
            port=1883,
            to_pubsub_topic="test_in",
            from_pubsub_topic="test_out",
        )

        handler = MqttHandler("test", config, logger)

        # First test: connection error
        mock_client.connect.side_effect = ConnectionRefusedError()
        result = await handler._handle_connection_error("test_id")
        assert result is False
        logger.warning.assert_called_once()

        # Second test: successful reconnection
        mock_client.connect.side_effect = None
        mock_client.connect.reset_mock()
        logger.warning.reset_mock()
        result = await handler._handle_connection_error("test_id")
        assert result is True
        mock_client.connect.assert_called_once()
        logger.warning.assert_not_called()


@pytest.mark.asyncio
async def test_mqtt_message_handling():
    logger = MagicMock()
    config = MqttHandlerConfig(
        host="localhost",
        port=1883,
        to_pubsub_topic="test_in",
        from_pubsub_topic="test_out",
    )

    with patch("paho.mqtt.client.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        handler = MqttHandler("test", config, logger)

        # Test message handling with bytes payload
        message = MagicMock()
        message.payload = json.dumps(
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

        await handler._add_message_to_queue(message)

        # Verify message was added to queue
        queued_message = await handler._message_queue.get()
        assert queued_message.content == {"data": "test"}
        assert queued_message.header.message_id == "msg1"
        assert queued_message.header.channel == "test_channel"
        assert queued_message.header.origin_id == "test_client"


@pytest.mark.asyncio
async def test_mqtt_subscription_management():
    logger = MagicMock()
    config = MqttHandlerConfig(
        host="localhost",
        port=1883,
        to_pubsub_topic="test_in",
        from_pubsub_topic="test_out",
    )

    with patch("paho.mqtt.client.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        handler = MqttHandler("test", config, logger)

        # Test subscribe multiple clients to multiple channels
        handler.subscribe("channel1", "client1")
        handler.subscribe("channel2", "client1")
        handler.subscribe("channel1", "client2")

        # Reset subscribe call count for clearer testing
        mock_client.subscribe.reset_mock()
        mock_client.unsubscribe.reset_mock()

        # Test case 1: Unsubscribe all clients from a channel
        handler.unsubscribe(channel_name="channel1")
        # Should unsubscribe both client1 and client2
        assert mock_client.unsubscribe.call_count == 2
        assert "channel1" not in handler._subscribed_channels
        # client1 should still be subscribed to channel2
        assert "client1" in handler._subscribed_channels["channel2"]

        mock_client.unsubscribe.reset_mock()

        # Test case 2: Unsubscribe from non-existent channel
        handler.unsubscribe(channel_name="non_existent_channel")
        # Should log warning and not call unsubscribe
        logger.warning.assert_called_with(
            "Attempted to unsubscribe from non-existent channel: non_existent_channel"
        )
        assert mock_client.unsubscribe.call_count == 0

        mock_client.unsubscribe.reset_mock()
        logger.warning.reset_mock()

        # Test case 3: Unsubscribe specific client
        handler.unsubscribe(handler_id="client1")
        # Should unsubscribe from channel2 (channel1 was already unsubscribed)
        mock_client.unsubscribe.assert_called_once_with("test_in/client1")
        assert "channel2" not in handler._subscribed_channels

        # Verify final state
        assert len(handler._subscribed_channels) == 0


@pytest.mark.asyncio
async def test_mqtt_send_message():
    logger = MagicMock()
    config = MqttHandlerConfig(
        host="localhost",
        port=1883,
        to_pubsub_topic="test_in",
        from_pubsub_topic="test_out",
    )

    with patch("paho.mqtt.client.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        handler = MqttHandler("test", config, logger)

        # Test successful send
        mock_result = MagicMock()
        mock_result.rc = 0  # Success
        mock_client.publish.return_value = mock_result

        await handler._send(
            "client1",
            {"data": "test"},
            {"message_id": "msg1", "origin_id": "test_client"},
        )

        mock_client.publish.assert_called_with(
            "test_out/client1",
            payload=json.dumps(
                {
                    "content": {"data": "test"},
                    "header": {"message_id": "msg1", "origin_id": "test_client"},
                }
            ),
        )

        # Test connection error
        mock_result.rc = mqtt.MQTT_ERR_NO_CONN
        mock_client.publish.return_value = mock_result

        with pytest.raises(HandlerConnectionError):
            await handler._send(
                "client1",
                {"data": "test"},
                {"message_id": "msg1", "origin_id": "test_client"},
            )
