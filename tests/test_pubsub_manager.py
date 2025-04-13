import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest


@pytest.mark.asyncio
async def test_subscribe_unsubscribe(test_pubsub_manager):
    await test_pubsub_manager._subscribe("test")
    calls = [call("test"), call("123/test")]
    test_pubsub_manager._broker.subscribe.assert_has_awaits(calls)

    await test_pubsub_manager._unsubscribe("test")
    calls = [call("test"), call("123/test")]
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

    # Verify subscription was processed
    test_pubsub_manager._broker.subscribe.assert_has_awaits(
        [call("test_channel"), call("123/test_channel")]
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
