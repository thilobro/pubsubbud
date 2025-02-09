from pubsubbud import pubsub_handler, callback_handler, websocket_handler
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_pubsub_handler():

    async def test_callback(content, header):
        print("Executed callback")
        print(content)
        print(header)

    ps_handler = pubsub_handler.PubsubHandler("123")
    ps_handler._pubsub = AsyncMock()
    await ps_handler.subscribe("test")
    ps_handler.run()
    ps_handler.close()
