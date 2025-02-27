import json
from unittest.mock import AsyncMock, Mock

import pytest

from pubsubbud.config import WebsocketHandlerConfig
from pubsubbud.handler.websocket_handler import WebsocketHandler


@pytest.mark.asyncio
async def test_run_stop(test_logger):
    config = WebsocketHandlerConfig(host="localhost", port=8675)
    ws_handler = WebsocketHandler("websocket", config, test_logger)
    ws_handler.run()
    await ws_handler.stop()


@pytest.mark.asyncio
async def test_publish(test_logger):
    config = WebsocketHandlerConfig(host="localhost", port=8675)
    ws_handler = WebsocketHandler("websocket", config, test_logger)
    ws_handler.run()
    mock_socket_id = "123"
    test_content = {"content": "test"}
    test_header = {"header": "test"}
    mock_socket = Mock()
    mock_socket.id = mock_socket_id
    mock_socket.send = AsyncMock()
    ws_handler._connect(mock_socket)
    await ws_handler.publish(mock_socket_id, test_content, test_header)
    mock_socket.send.assert_called_once_with(
        json.dumps({"content": test_content, "header": test_header})
    )
    await ws_handler.stop()
