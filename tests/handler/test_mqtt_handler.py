from unittest.mock import MagicMock, patch

import pytest

from pubsubbud.config import MqttHandlerConfig
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
