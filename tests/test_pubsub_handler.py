from unittest.mock import call

import pytest


@pytest.mark.asyncio
async def test_subscribe_unsubscribe(test_pubsub_handler, test_callback_interface):
    await test_pubsub_handler.subscribe("test")
    calls = [call("test"), call("123/test")]
    test_pubsub_handler._pubsub.subscribe.assert_has_awaits(calls)

    await test_pubsub_handler.unsubscribe("test")
    calls = [call("test"), call("123/test")]
    test_pubsub_handler._pubsub.unsubscribe.assert_has_awaits(calls)

    test_pubsub_handler.add_interface(test_callback_interface)
    await test_pubsub_handler.subscribe(
        "test", interface_name="callback", interface_id="test_id"
    )
    assert test_pubsub_handler._interfaces["callback"].has_subscribers("test")

    await test_pubsub_handler.unsubscribe(
        "test", interface_name="callback", interface_id="test_id"
    )
    assert not test_pubsub_handler._interfaces["callback"].has_subscribers("test")


@pytest.mark.asyncio
async def test_run_close(test_pubsub_handler):
    test_pubsub_handler.run()
    test_pubsub_handler.close()
