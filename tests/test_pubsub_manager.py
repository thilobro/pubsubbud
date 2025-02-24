from unittest.mock import call

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
