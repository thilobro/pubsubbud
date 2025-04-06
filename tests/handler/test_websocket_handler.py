import json
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import websockets

from pubsubbud.config import WebsocketHandlerConfig
from pubsubbud.handler.handler_interface import HandlerConnectionError
from pubsubbud.handler.websocket_handler import WebsocketHandler


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


@pytest.mark.asyncio
async def test_websocket_handler_connection_error():
    logger = MagicMock()
    config = WebsocketHandlerConfig(host="localhost", port=8765)
    handler = WebsocketHandler("test", config, logger)

    # Test immediate failure on connection error
    assert await handler._handle_connection_error("test_id") is False

    # Test publish raises HandlerConnectionError when connection not found
    with pytest.raises(HandlerConnectionError):
        await handler._send("nonexistent_id", {}, {})


@pytest.mark.asyncio
async def test_websocket_message_handling(test_websocket_handler):
    # Setup mock websocket
    mock_socket = AsyncMock()
    mock_socket.id = "123"

    # Create messages list with required fields
    messages = [
        '{"content": {"data": "test"}, "header": {"message_id": "msg1", "channel": "test_channel", "type": "test"}}',
        b'{"content": {"data": "test2"}, "header": {"message_id": "msg2", "channel": "test_channel", "type": "test2"}}',
    ]

    # Mock the __aiter__ to return messages
    mock_socket.__aiter__.return_value = messages

    try:
        # Handle messages until ConnectionClosedOK
        await test_websocket_handler._handle_websocket(mock_socket)
    except websockets.exceptions.ConnectionClosedOK:
        pass

    # Get messages from queue
    message1 = await test_websocket_handler._message_queue.get()
    assert message1.content == {"data": "test"}
    assert message1.header.origin_id == "123"
    assert message1.header.message_id == "msg1"
    assert message1.header.channel == "test_channel"

    message2 = await test_websocket_handler._message_queue.get()
    assert message2.content == {"data": "test2"}
    assert message2.header.origin_id == "123"
    assert message2.header.message_id == "msg2"
    assert message2.header.channel == "test_channel"
