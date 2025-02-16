from unittest.mock import call

import pytest


@pytest.mark.asyncio
async def test_subscribe_unsubscribe(test_pubsub_handler):
    await test_pubsub_handler.subscribe("test")
    calls = [call("test"), call("123/test")]
    test_pubsub_handler._pubsub.subscribe.assert_has_awaits(calls)

    await test_pubsub_handler.unsubscribe("test")
    calls = [call("test"), call("123/test")]
    test_pubsub_handler._pubsub.unsubscribe.assert_has_awaits(calls)


@pytest.mark.asyncio
async def test_run_close(test_pubsub_handler):
    test_pubsub_handler.run()
    await test_pubsub_handler.close()
