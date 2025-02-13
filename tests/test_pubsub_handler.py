from unittest.mock import AsyncMock

import pytest

from pubsubbud import pubsub_handler
from pubsubbud.config import PubsubHandlerConfig


@pytest.mark.asyncio
async def test_pubsub_handler(test_logger):

    async def test_callback(content, header):
        print("Executed callback")
        print(content)
        print(header)

    ps_handler = pubsub_handler.PubsubHandler(
        config=PubsubHandlerConfig(uuid="123"), logger=test_logger
    )
    ps_handler._pubsub = AsyncMock()
    await ps_handler.subscribe("test")
    ps_handler.run()
    ps_handler.close()
