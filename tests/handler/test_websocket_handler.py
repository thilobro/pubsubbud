import asyncio
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


@pytest.mark.asyncio
async def test_websocket_handler_publish_error_handling(test_websocket_handler):
    """Test error handling in publish method."""
    # Mock _publish_callback to raise an error
    test_websocket_handler._publish_callback = AsyncMock(
        side_effect=HandlerConnectionError("Test error")
    )
    test_websocket_handler._handle_connection_error = AsyncMock(return_value=False)

    await test_websocket_handler.publish("test_id", {}, {})

    # Verify error handling was attempted
    test_websocket_handler._handle_connection_error.assert_awaited_once_with("test_id")


@pytest.mark.asyncio
async def test_websocket_handler_unsubscribe_error_handling(test_websocket_handler):
    """Test error handling in unsubscribe method."""
    # Subscribe to create the channel
    test_websocket_handler.subscribe("test_channel", "client1")

    # Try to unsubscribe from non-existent channel
    test_websocket_handler.unsubscribe("nonexistent_channel", "client1")

    # Try to unsubscribe non-existent client
    test_websocket_handler.unsubscribe("test_channel", "nonexistent_client")

    # Verify no errors were raised and handler is still in valid state
    assert test_websocket_handler.has_subscribers("test_channel")


@pytest.mark.asyncio
async def test_websocket_handler_connection_error_handling(test_websocket_handler):
    """Test connection error handling."""
    # Verify immediate failure for websocket handler
    result = await test_websocket_handler._handle_connection_error("test_id")
    assert result is False


@pytest.mark.asyncio
async def test_websocket_handler_stop(test_websocket_handler):
    """Test stop method."""
    # Create a task to stop
    test_websocket_handler._run_task = asyncio.create_task(asyncio.sleep(1))
    test_websocket_handler._logger.info = MagicMock()

    # Stop the handler
    await test_websocket_handler.stop()

    # Verify task was cancelled
    assert test_websocket_handler._run_task.cancelled()
    test_websocket_handler._logger.info.assert_called_with(
        f"Interface {test_websocket_handler._name} stopped."
    )
