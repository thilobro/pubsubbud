import json
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.mark.asyncio
async def test_run_stop(test_websocket_handler):
    test_websocket_handler.run()
    await test_websocket_handler.stop()


@pytest.mark.asyncio
async def test_publish(test_websocket_handler):
    test_websocket_handler.run()
    mock_socket_id = "123"
    test_content = {"content": "test"}
    test_header = {"header": "test"}
    mock_socket = Mock()
    mock_socket.id = mock_socket_id
    mock_socket.send = AsyncMock()
    test_websocket_handler._connect(mock_socket)
    await test_websocket_handler.publish(mock_socket_id, test_content, test_header)
    mock_socket.send.assert_called_once_with(
        json.dumps({"content": test_content, "header": test_header})
    )
    await test_websocket_handler.stop()
