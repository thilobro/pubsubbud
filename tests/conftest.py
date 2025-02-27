import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from pubsubbud.config import PubsubManagerConfig, WebsocketHandlerConfig
from pubsubbud.handler.websocket_handler import WebsocketHandler
from pubsubbud.pubsub_manager import PubsubManager


class AsyncContextManager(MagicMock):
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, traceback):
        pass


@pytest.fixture
def test_websocket_handler(test_logger):
    config = WebsocketHandlerConfig(host="localhost", port=8675)
    return WebsocketHandler("websocket", config, test_logger)


@pytest.fixture
def test_pubsub_manager(test_logger):
    test_broker = None
    ps_manager = PubsubManager(
        config=PubsubManagerConfig(uuid="123"), broker=test_broker, logger=test_logger
    )
    ps_manager._broker = AsyncMock()
    ps_manager._broker.read_messages = AsyncContextManager()
    return ps_manager


@pytest.fixture
def test_logger():
    return logging.getLogger("test_logger")
