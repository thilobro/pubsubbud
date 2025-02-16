import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from pubsubbud import pubsub_handler
from pubsubbud.config import PubsubHandlerConfig


class AsyncContextManager(MagicMock):
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, traceback):
        pass


@pytest.fixture
def test_pubsub_handler(test_logger):
    ps_handler = pubsub_handler.PubsubHandler(
        config=PubsubHandlerConfig(uuid="123"), logger=test_logger
    )
    ps_handler._pubsub = AsyncMock()
    ps_handler._pubsub.listen = AsyncContextManager()
    return ps_handler


@pytest.fixture
def test_logger():
    return logging.getLogger("test_logger")
