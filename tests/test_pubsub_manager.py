import asyncio
import http
import json
import logging
import uuid
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from pubsubbud.handler.handler_interface import (
    ContentValidationCallback,
    HandlerInterface,
)
from pubsubbud.models import BrokerMessage


@pytest.mark.asyncio
async def test_subscribe_unsubscribe(test_pubsub_manager):
    await test_pubsub_manager._subscribe("test")
    uuid = test_pubsub_manager._uuid  # Get the actual UUID
    calls = [call("test"), call(f"{uuid}/test")]
    test_pubsub_manager._broker.subscribe.assert_has_awaits(calls)

    await test_pubsub_manager._unsubscribe("test")
    calls = [call("test"), call(f"{uuid}/test")]
    test_pubsub_manager._broker.unsubscribe.assert_has_awaits(calls)


@pytest.mark.asyncio
async def test_run_close(test_pubsub_manager):
    test_pubsub_manager.run()
    await test_pubsub_manager.close()


@pytest.mark.asyncio
async def test_register_unregister_callback(test_pubsub_manager):
    async def test_callback(content, header):
        pass

    async def test_callback2(content, header):
        pass

    test_channel = "test_channel"

    # add callback
    await test_pubsub_manager.register_callback(test_channel, test_callback)
    assert len(test_pubsub_manager._callbacks[test_channel]) == 1
    assert len(test_pubsub_manager._callbacks.keys()) == 1
    assert test_callback in test_pubsub_manager._callbacks[test_channel]

    # remove callback
    await test_pubsub_manager.unregister_callback(test_channel, test_callback)
    assert test_channel not in test_pubsub_manager._callbacks.keys()

    # add two callbacks
    await test_pubsub_manager.register_callback(test_channel, test_callback)
    await test_pubsub_manager.register_callback(test_channel, test_callback2)
    assert len(test_pubsub_manager._callbacks[test_channel]) == 2
    assert len(test_pubsub_manager._callbacks.keys()) == 1
    assert test_callback in test_pubsub_manager._callbacks[test_channel]
    assert test_callback2 in test_pubsub_manager._callbacks[test_channel]

    # remove one callback
    await test_pubsub_manager.unregister_callback(test_channel, test_callback)
    assert test_callback not in test_pubsub_manager._callbacks[test_channel]
    assert test_callback2 in test_pubsub_manager._callbacks[test_channel]

    # remove second callback
    await test_pubsub_manager.unregister_callback(test_channel, test_callback2)
    assert test_channel not in test_pubsub_manager._callbacks.keys()

    # add two callbacks
    await test_pubsub_manager.register_callback(test_channel, test_callback)
    await test_pubsub_manager.register_callback(test_channel, test_callback2)
    assert len(test_pubsub_manager._callbacks[test_channel]) == 2
    assert len(test_pubsub_manager._callbacks.keys()) == 1
    assert test_callback in test_pubsub_manager._callbacks[test_channel]
    assert test_callback2 in test_pubsub_manager._callbacks[test_channel]

    # remove all callbacks for test channel
    await test_pubsub_manager.unregister_callback(test_channel)
    assert test_channel not in test_pubsub_manager._callbacks.keys()


@pytest.mark.asyncio
async def test_message_processing(test_pubsub_manager):
    # Setup mock message
    mock_message = MagicMock()
    mock_message.header.channel = "test_channel"
    mock_message.content = {"test": "data"}
    mock_message.header.dict.return_value = {"channel": "test_channel"}

    # Setup broker to yield our test message
    test_pubsub_manager._broker.read_messages.return_value.__aiter__.return_value = [
        mock_message
    ]

    # Setup callback
    received_messages = []

    async def test_callback(content, header):
        received_messages.append((content, header))

    await test_pubsub_manager.register_callback("test_channel", test_callback)
    test_pubsub_manager.run()
    await asyncio.sleep(0.1)

    assert len(received_messages) == 1
    assert received_messages[0][0] == {"test": "data"}


@pytest.mark.asyncio
async def test_handler_message_forwarding(test_pubsub_manager):
    # Create mock handler instead of using test_websocket_handler
    mock_handler = MagicMock()
    mock_handler.name = "test_handler"
    mock_handler.publish_if_subscribed = AsyncMock()
    test_pubsub_manager.add_handler(mock_handler)

    # Setup mock message
    mock_message = MagicMock()
    mock_message.header.channel = "test_channel"
    mock_message.content = {"test": "data"}
    mock_message.header.dict.return_value = {"channel": "test_channel"}

    test_pubsub_manager._broker.read_messages.return_value.__aiter__.return_value = [
        mock_message
    ]
    test_pubsub_manager.run()
    await asyncio.sleep(0.1)

    # Verify handler received the message
    mock_handler.publish_if_subscribed.assert_awaited_once()


@pytest.mark.asyncio
async def test_channel_cleanup(test_pubsub_manager):
    async def test_callback(content, header):
        pass

    # Register and immediately unregister
    await test_pubsub_manager.register_callback("test_channel", test_callback)

    # Verify channel was added
    assert "test_channel" in test_pubsub_manager._channels

    # Unregister and cleanup
    await test_pubsub_manager.unregister_callback("test_channel")

    # Verify cleanup occurred
    assert "test_channel" not in test_pubsub_manager._channels
    test_pubsub_manager._broker.unsubscribe.assert_called()


@pytest.mark.asyncio
async def test_subscription_message_handling(
    test_pubsub_manager, test_websocket_handler
):
    test_pubsub_manager.add_handler(test_websocket_handler)

    # Setup subscription message
    mock_message = MagicMock()
    mock_message.header.channel = "subscription"
    mock_message.header.origin_id = "test_id"
    mock_message.header.message_id = "msg_id"
    mock_message.content = {
        "subscription_type": "subscription",
        "subscription_channel": "test_channel",
    }

    await test_pubsub_manager._handle_subscription_message(
        mock_message, test_websocket_handler.name, "test_id"
    )

    # Verify subscription was processed using actual UUID
    uuid = test_pubsub_manager._uuid  # Get the actual UUID
    test_pubsub_manager._broker.subscribe.assert_has_awaits(
        [call("test_channel"), call(f"{uuid}/test_channel")]
    )


@pytest.mark.asyncio
async def test_multiple_handlers(test_pubsub_manager):
    # Create multiple mock handlers
    handlers = []
    for i in range(3):
        handler = MagicMock()
        handler.name = f"handler_{i}"
        handler.publish_if_subscribed = AsyncMock()

        # Add actual subscriptions instead of mocking has_subscribers
        handler.subscriptions = {"test_channel": set(["client1", "client2"])}
        handler.has_subscribers = lambda x: x in handler.subscriptions

        handlers.append(handler)
        test_pubsub_manager.add_handler(handler)

    # Create test message
    mock_message = MagicMock()
    mock_message.header.channel = "test_channel"
    mock_message.content = {"test": "data"}
    mock_message.header.dict.return_value = {"channel": "test_channel"}

    test_pubsub_manager._broker.read_messages.return_value.__aiter__.return_value = [
        mock_message
    ]

    test_pubsub_manager.run()
    await asyncio.sleep(0.1)

    # Verify all handlers were called
    for handler in handlers:
        handler.publish_if_subscribed.assert_awaited_once_with(
            "test_channel", {"test": "data"}, {"channel": "test_channel"}
        )


@pytest.mark.asyncio
async def test_pattern_callback_registration(test_pubsub_manager):
    async def test_callback(content, header):
        pass

    # Register pattern callback
    await test_pubsub_manager.register_callback("test.*", test_callback)
    assert "test.*" in test_pubsub_manager._pattern_callbacks
    assert len(test_pubsub_manager._pattern_callbacks["test.*"]) == 1
    assert test_callback in test_pubsub_manager._pattern_callbacks["test.*"]

    # Register another callback for same pattern
    async def test_callback2(content, header):
        pass

    await test_pubsub_manager.register_callback("test.*", test_callback2)
    assert len(test_pubsub_manager._pattern_callbacks["test.*"]) == 2


@pytest.mark.asyncio
async def test_pattern_callback_matching(test_pubsub_manager):
    received_messages = []

    async def test_callback(content, header):
        received_messages.append((content, header))

    # Register pattern callback
    await test_pubsub_manager.register_callback("test.*", test_callback)

    # Test matching patterns
    test_patterns = [
        ("test.123", True),
        ("test.abc", True),
        ("test", False),
        ("other.123", False),
        ("test.123.456", True),
    ]

    for channel, should_match in test_patterns:
        mock_message = MagicMock()
        mock_message.header.channel = channel
        mock_message.content = {"test": "data"}
        mock_message.header.dict.return_value = {"channel": channel}

        test_pubsub_manager._broker.read_messages.return_value.__aiter__.return_value = [
            mock_message
        ]
        test_pubsub_manager.run()
        await asyncio.sleep(0.1)

        if should_match:
            assert len(received_messages) == 1
            assert received_messages[0][0] == {"test": "data"}
            received_messages.clear()
        else:
            assert len(received_messages) == 0


@pytest.mark.asyncio
async def test_multiple_pattern_callbacks(test_pubsub_manager):
    received_messages = []

    async def test_callback1(content, header):
        received_messages.append(("callback1", content, header))

    async def test_callback2(content, header):
        received_messages.append(("callback2", content, header))

    # Register multiple pattern callbacks
    await test_pubsub_manager.register_callback("test.*", test_callback1)
    await test_pubsub_manager.register_callback("*.123", test_callback2)

    # Test message that matches both patterns
    mock_message = MagicMock()
    mock_message.header.channel = "test.123"
    mock_message.content = {"test": "data"}
    mock_message.header.dict.return_value = {"channel": "test.123"}

    test_pubsub_manager._broker.read_messages.return_value.__aiter__.return_value = [
        mock_message
    ]
    test_pubsub_manager.run()
    await asyncio.sleep(0.1)

    assert len(received_messages) == 2
    assert ("callback1", {"test": "data"}, {"channel": "test.123"}) in received_messages
    assert ("callback2", {"test": "data"}, {"channel": "test.123"}) in received_messages


@pytest.mark.asyncio
async def test_pattern_callback_cleanup(test_pubsub_manager):
    async def test_callback(content, header):
        pass

    # Register pattern callback
    await test_pubsub_manager.register_callback("test.*", test_callback)
    assert "test.*" in test_pubsub_manager._pattern_callbacks

    # Unregister callback
    await test_pubsub_manager.unregister_callback("test.*", test_callback)
    assert "test.*" not in test_pubsub_manager._pattern_callbacks


@pytest.mark.asyncio
async def test_pattern_and_exact_callback(test_pubsub_manager):
    received_messages = []

    async def pattern_callback(content, header):
        received_messages.append(("pattern", content, header))

    async def exact_callback(content, header):
        received_messages.append(("exact", content, header))

    # Register both pattern and exact callbacks
    await test_pubsub_manager.register_callback("test.*", pattern_callback)
    await test_pubsub_manager.register_callback("test.123", exact_callback)

    # Test message that matches both
    mock_message = MagicMock()
    mock_message.header.channel = "test.123"
    mock_message.content = {"test": "data"}
    mock_message.header.dict.return_value = {"channel": "test.123"}

    test_pubsub_manager._broker.read_messages.return_value.__aiter__.return_value = [
        mock_message
    ]
    test_pubsub_manager.run()
    await asyncio.sleep(0.1)

    assert len(received_messages) == 2
    assert ("pattern", {"test": "data"}, {"channel": "test.123"}) in received_messages
    assert ("exact", {"test": "data"}, {"channel": "test.123"}) in received_messages


@pytest.mark.asyncio
async def test_invalid_subscription_message(
    test_pubsub_manager, test_websocket_handler
):
    """Test handling of invalid subscription messages."""
    test_pubsub_manager.add_handler(test_websocket_handler)

    # Test invalid subscription type
    mock_message = MagicMock()
    mock_message.header.channel = "subscription"
    mock_message.header.origin_id = "test_id"
    mock_message.header.message_id = "msg_id"
    mock_message.content = {
        "subscription_type": "invalid_type",
        "subscription_channel": "test_channel",
    }

    with pytest.raises(
        ValueError, match="Subscription type not supported: invalid_type"
    ):
        await test_pubsub_manager._handle_subscription_message(
            mock_message, test_websocket_handler.name, "test_id"
        )


@pytest.mark.asyncio
async def test_handler_message_processing_error(test_pubsub_manager):
    """Test error handling in handler message processing."""
    mock_handler = MagicMock()
    mock_handler.name = "test_handler"
    mock_handler.message_iterator = AsyncMock()
    mock_handler.publish = AsyncMock()
    test_pubsub_manager.add_handler(mock_handler)

    # Create a message that will cause an error
    error_message = MagicMock()
    error_message.header.channel = "test_channel"
    error_message.header.origin_id = "test_id"
    error_message.header.message_id = "msg_id"
    error_message.content = {"data": "test"}

    # Make the handler raise an exception when processing the message
    async def raise_error(*args, **kwargs):
        raise Exception("Test error")

    mock_handler.message_iterator.__aiter__.return_value = [error_message]
    test_pubsub_manager._handle_pubsub_message = AsyncMock(side_effect=raise_error)

    # Start processing messages
    task = asyncio.create_task(test_pubsub_manager._get_handler_messages(mock_handler))
    await asyncio.sleep(0.1)

    # Verify error handling
    mock_handler.publish.assert_awaited_with(
        "test_id",
        {},
        {"ack_id": "msg_id", "status_code": http.HTTPStatus.INTERNAL_SERVER_ERROR},
    )

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_specific_handler_forwarding(test_pubsub_manager):
    """Test message forwarding to specific handlers."""
    # Create two mock handlers
    handler1 = MagicMock()
    handler1.name = "handler1"
    handler1.publish = AsyncMock()

    handler2 = MagicMock()
    handler2.name = "handler2"
    handler2.publish = AsyncMock()

    test_pubsub_manager.add_handler(handler1)
    test_pubsub_manager.add_handler(handler2)

    # Test forwarding to specific handler
    content = {"test": "data"}
    header = {"type": "test"}

    await test_pubsub_manager.forward_to_handlers(
        "test_channel", content, header, handler_id="client1", handler_type="handler1"
    )

    # Verify only handler1 received the message
    handler1.publish.assert_awaited_once_with(
        handler_id="client1", content=content, header=header
    )
    handler2.publish.assert_not_awaited()

    # Test invalid handler forwarding
    # Create a mock logger
    mock_logger = MagicMock()
    test_pubsub_manager._logger = mock_logger

    await test_pubsub_manager.forward_to_handlers(
        "test_channel", content, header, handler_id="client1", handler_type=None
    )

    # Verify warning was logged
    mock_logger.warning.assert_called_once_with(
        "Unable to foward to handler for handler id client1 and handler type None. Both must be set to forward to a specific client."
    )


@pytest.mark.asyncio
async def test_internal_message_publishing(test_pubsub_manager):
    """Test publishing internal messages."""
    # Test internal message
    await test_pubsub_manager.publish("test_channel", {"test": "data"}, internal=True)

    # Get the actual call arguments
    actual_topic, actual_message_json = test_pubsub_manager._broker.publish.call_args[0]
    actual_message = json.loads(actual_message_json)

    # Verify the topic
    assert actual_topic == f"{test_pubsub_manager._uuid}/test_channel"

    # Verify the message structure
    assert actual_message["content"] == {"test": "data"}
    assert actual_message["header"]["channel"] == "test_channel"
    assert actual_message["header"]["origin_id"] == test_pubsub_manager._uuid
    # message_id is random, just verify it exists
    assert "message_id" in actual_message["header"]
    assert "timestamp" in actual_message["header"]


@pytest.mark.asyncio
async def test_handler_task_management(test_pubsub_manager):
    """Test handler task management."""
    # Create mock handler
    mock_handler = MagicMock()
    mock_handler.name = "test_handler"
    mock_handler.message_iterator = AsyncMock()
    mock_handler.run = MagicMock()
    test_pubsub_manager.add_handler(mock_handler)

    # Run handler tasks
    test_pubsub_manager._run_handler_tasks()

    # Verify handler was started
    mock_handler.run.assert_called_once()
    assert "test_handler" in test_pubsub_manager._handler_tasks

    # Clean up
    for task in test_pubsub_manager._handler_tasks.values():
        task.cancel()


@pytest.mark.asyncio
async def test_callback_execution_error(test_pubsub_manager):
    """Test error handling during callback execution."""
    # Replace the logger with a mock
    mock_logger = MagicMock()
    test_pubsub_manager._logger = mock_logger

    async def failing_callback(content, header):
        raise Exception("Test callback error")

    # Register the failing callback
    await test_pubsub_manager.register_callback("test_channel", failing_callback)

    # Create a test message
    mock_message = MagicMock()
    mock_message.header.channel = "test_channel"
    mock_message.content = {"test": "data"}
    mock_message.header.dict.return_value = {"channel": "test_channel"}

    # Execute callbacks
    await test_pubsub_manager._execute_callbacks(
        "test_channel", mock_message.content, mock_message.header.dict()
    )

    # Verify warning was logged
    mock_logger.warning.assert_called_with("Error executing callback.", exc_info=True)


@pytest.mark.asyncio
async def test_handler_task_cleanup(test_pubsub_manager):
    """Test cleanup of handler tasks."""
    # Create mock handlers
    handler1 = MagicMock()
    handler1.name = "handler1"
    handler1.stop = AsyncMock()

    handler2 = MagicMock()
    handler2.name = "handler2"
    handler2.stop = AsyncMock()

    test_pubsub_manager.add_handler(handler1)
    test_pubsub_manager.add_handler(handler2)

    # Create and store tasks that we can verify are cancelled
    async def long_running_task():
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            raise

    test_pubsub_manager._handler_tasks = {
        "handler1": asyncio.create_task(long_running_task()),
        "handler2": asyncio.create_task(long_running_task()),
    }

    # Close the manager
    await test_pubsub_manager.close()

    # Give a short time for tasks to be cancelled
    await asyncio.sleep(0.1)

    # Verify all tasks were cancelled and handlers stopped
    assert all(task.cancelled() for task in test_pubsub_manager._handler_tasks.values())
    handler1.stop.assert_awaited_once()
    handler2.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_message_task_restart(test_pubsub_manager):
    """Test message task restart functionality."""
    # Create initial message task
    test_pubsub_manager._run_message_task()
    original_task = test_pubsub_manager._message_task

    # Restart the task
    await test_pubsub_manager._restart_message_task()

    # Verify original task was cancelled and new task created
    assert original_task.cancelled()
    assert test_pubsub_manager._message_task is not None
    assert test_pubsub_manager._message_task is not original_task


@pytest.mark.asyncio
async def test_handler_message_processing_subscription(test_pubsub_manager):
    """Test processing of subscription messages from handlers."""
    mock_handler = MagicMock()
    mock_handler.name = "test_handler"
    mock_handler.message_iterator = AsyncMock()
    mock_handler.publish = AsyncMock()
    test_pubsub_manager.add_handler(mock_handler)

    # Create a subscription message
    sub_message = MagicMock()
    sub_message.header.channel = "subscription"
    sub_message.header.origin_id = "test_id"
    sub_message.header.message_id = "msg_id"
    sub_message.content = {
        "subscription_type": "subscription",
        "subscription_channel": "test_channel",
    }

    # Set up the handler to yield our test message
    mock_handler.message_iterator.__aiter__.return_value = [sub_message]

    # Start processing messages
    task = asyncio.create_task(test_pubsub_manager._get_handler_messages(mock_handler))
    await asyncio.sleep(0.1)

    # Verify subscription was processed
    mock_handler.publish.assert_awaited_with(
        "test_id", {}, {"ack_id": "msg_id", "status_code": http.HTTPStatus.OK}
    )

    # Clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_unsubscribe_nonexistent_channel(test_pubsub_manager):
    """Test unsubscribing from a non-existent channel."""
    # Try to unsubscribe from non-existent channel
    await test_pubsub_manager._unsubscribe("nonexistent_channel")

    # Verify broker unsubscribe was not called
    test_pubsub_manager._broker.unsubscribe.assert_not_called()


@pytest.mark.asyncio
async def test_forward_to_nonexistent_handler(test_pubsub_manager):
    """Test forwarding to non-existent handler type."""
    # Replace the logger with a mock
    mock_logger = MagicMock()
    test_pubsub_manager._logger = mock_logger

    content = {"test": "data"}
    header = {"type": "test"}

    # Try to forward to non-existent handler
    await test_pubsub_manager.forward_to_handlers(
        "test_channel",
        content,
        header,
        handler_id="client1",
        handler_type="nonexistent_handler",
    )

    # Verify warning was logged with correct message
    mock_logger.warning.assert_called_once_with(
        "Unable to forward to handler nonexistent_handler with id client1. Handler not found."
    )


@pytest.mark.asyncio
async def test_validation_callback_in_pubsub_manager(test_pubsub_manager):
    """Test validation callback in PubsubManager."""

    # Setup validation callback
    def validation_callback(content: dict) -> bool:
        return "valid" in content

    # Create a test handler with validation
    handler = TestHandler(
        name="test",
        publish_callback=AsyncMock(),
        logger=logging.getLogger("test_logger"),
        content_validation_callback=validation_callback,
    )
    test_pubsub_manager.add_handler(handler)

    # Subscribe handler to test channel
    handler.subscribe("test_channel", "test_client")

    # Create test messages
    valid_message = BrokerMessage(
        channel="test_channel",
        content={"valid": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )
    invalid_message = BrokerMessage(
        channel="test_channel",
        content={"invalid": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )

    # Process messages directly through forward_to_handlers
    await test_pubsub_manager.forward_to_handlers(
        "test_channel",
        valid_message.content,
        valid_message.header,
    )
    await test_pubsub_manager.forward_to_handlers(
        "test_channel",
        invalid_message.content,
        invalid_message.header,
    )

    # Verify handler received valid message
    assert handler._publish_callback.call_count == 1


@pytest.mark.asyncio
async def test_validation_error_handling(test_pubsub_manager):
    """Test error handling for validation failures."""

    # Setup validation callback
    def validation_callback(content: dict) -> bool:
        return "valid" in content

    # Create a test handler with validation
    handler = TestHandler(
        name="test",
        publish_callback=AsyncMock(),
        logger=logging.getLogger("test_logger"),
        content_validation_callback=validation_callback,
    )
    test_pubsub_manager.add_handler(handler)

    # Create an invalid message
    invalid_message = BrokerMessage(
        channel="test_channel",
        content={"invalid": True},
        header={
            "message_id": "test_id",
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )

    # Test message processing
    await test_pubsub_manager._handle_pubsub_message(invalid_message)

    # Verify error handling
    assert handler._publish_callback.call_count == 0


@pytest.mark.asyncio
async def test_multiple_handlers_validation(test_pubsub_manager):
    """Test validation with multiple handlers."""

    # Setup validation callbacks
    def validation_callback1(content: dict) -> bool:
        return "valid1" in content

    def validation_callback2(content: dict) -> bool:
        return "valid2" in content

    # Create test handlers with different validation rules
    handler1 = TestHandler(
        name="test1",
        publish_callback=AsyncMock(),
        logger=logging.getLogger("test_logger"),
        content_validation_callback=validation_callback1,
    )
    handler2 = TestHandler(
        name="test2",
        publish_callback=AsyncMock(),
        logger=logging.getLogger("test_logger"),
        content_validation_callback=validation_callback2,
    )
    test_pubsub_manager.add_handler(handler1)
    test_pubsub_manager.add_handler(handler2)

    # Subscribe handlers to test channel
    handler1.subscribe("test_channel", "test_client1")
    handler2.subscribe("test_channel", "test_client2")

    # Create test messages
    message1 = BrokerMessage(
        channel="test_channel",
        content={"valid1": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )
    message2 = BrokerMessage(
        channel="test_channel",
        content={"valid2": True},
        header={
            "message_id": str(uuid.uuid4()),
            "channel": "test_channel",
            "origin_id": "test_origin",
        },
    )

    # Process messages directly through forward_to_handlers
    await test_pubsub_manager.forward_to_handlers(
        "test_channel",
        message1.content,
        message1.header,
    )
    await test_pubsub_manager.forward_to_handlers(
        "test_channel",
        message2.content,
        message2.header,
    )

    # Verify each handler only processes its valid messages
    assert handler1._publish_callback.call_count == 1
    assert handler2._publish_callback.call_count == 1
    # Verify the correct message content was processed
    handler1._publish_callback.assert_awaited_with(
        "test_client1",
        {"valid1": True},
        message1.header.dict(),
    )
    handler2._publish_callback.assert_awaited_with(
        "test_client2",
        {"valid2": True},
        message2.header.dict(),
    )


class TestHandler(HandlerInterface):
    """Test implementation of HandlerInterface for testing."""

    def __init__(
        self,
        name: str,
        publish_callback: AsyncMock,
        logger: logging.Logger,
        content_validation_callback: Optional[ContentValidationCallback] = None,
    ) -> None:
        """Initialize the test handler."""
        super().__init__(name, publish_callback, logger, content_validation_callback)
        self._publish_callback = publish_callback
        self.subscriptions = {}

    async def start(self) -> None:
        """Start the handler."""
        pass

    async def stop(self) -> None:
        """Stop the handler."""
        pass

    async def publish(self, channel: str, content: dict) -> None:
        """Publish a message."""
        pass

    def run(self) -> None:
        """Run the handler."""
        pass

    def subscribe(self, channel_name: str, handler_id: str) -> None:
        """Subscribe to a channel."""
        if channel_name not in self.subscriptions:
            self.subscriptions[channel_name] = set()
        self.subscriptions[channel_name].add(handler_id)

    def unsubscribe(self, channel_name: str, handler_id: Optional[str] = None) -> None:
        """Unsubscribe from a channel."""
        if channel_name in self.subscriptions:
            if handler_id:
                self.subscriptions[channel_name].discard(handler_id)
            else:
                del self.subscriptions[channel_name]

    def has_subscribers(self, channel_name: str) -> bool:
        """Check if a channel has subscribers."""
        return channel_name in self.subscriptions and bool(
            self.subscriptions[channel_name]
        )

    async def publish_if_subscribed(
        self, channel_name: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        """Publish a message to all subscribers of a channel."""
        if self.has_subscribers(channel_name):
            # Validate content if validation callback is set
            if (
                self._content_validation_callback
                and not self._content_validation_callback(content)
            ):
                return
            for handler_id in self.subscriptions[channel_name]:
                await self._publish_callback(handler_id, content, header)
