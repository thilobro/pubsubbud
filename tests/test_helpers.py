from pubsubbud.helpers import create_header
from pubsubbud.models import BrokerMessageHeader


def test_create_header():
    test_channel = "test_channel"
    test_header = create_header(test_channel)
    test_header = BrokerMessageHeader(**test_header)
    assert test_header.channel == test_channel
    assert test_header.origin_id == "pubsub"
