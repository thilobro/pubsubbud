import logging

import pytest


@pytest.fixture
def test_logger():
    return logging.getLogger("test_logger")
