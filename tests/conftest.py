import pytest
import logging


@pytest.fixture
def test_logger():
    return logging.getLogger("test_logger")
