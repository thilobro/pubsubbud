import logging
from unittest.mock import AsyncMock

import pytest

from pubsubbud import callback_handler, pubsub_handler
from pubsubbud.config import PubsubHandlerConfig


@pytest.fixture
def test_callback_interface(test_logger):
    async def callback(content, header):
        print("Executed callback")
        print(content)
        print(header)

    async def callback2(content, header):
        print("Executed callback2")
        print(content)
        print(header)

    cb_handler = callback_handler.CallbackHandler("callback", test_logger)
    cb_handler.register_callback("test_callback", callback)
    cb_handler.register_callback("test_callback", callback2)
    return cb_handler


@pytest.fixture
def test_pubsub_handler(test_logger):
    ps_handler = pubsub_handler.PubsubHandler(
        config=PubsubHandlerConfig(uuid="123"), logger=test_logger
    )
    ps_handler._pubsub = AsyncMock()
    return ps_handler


@pytest.fixture
def test_logger():
    return logging.getLogger("test_logger")
