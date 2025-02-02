from pubsubbud.pubsub_handler import PubsubHandler
import pytest


@pytest.mark.asyncio
async def test_pubsub_handler():

    async def test_callback(message):
        print("TEST")

    ps_handler = PubsubHandler()
    await ps_handler.sub_channel("test", test_callback)
    ps_handler.run()
    ps_handler.close()
