import pytest


@pytest.mark.asyncio
async def test_broker_interface_abstract_methods():
    """Test broker interface abstract methods."""
    from pubsubbud.broker.broker_interface import BrokerInterface

    # Create a concrete implementation for testing that's missing the subscribe method
    class TestBroker(BrokerInterface):
        async def publish(self, channel: str, message: str) -> None:
            pass

        async def unsubscribe(self, channel: str) -> None:
            pass

        async def close(self) -> None:
            pass

        async def read_messages(self):
            yield None

    # Test that abstract methods must be implemented
    with pytest.raises(
        TypeError,
        match="Can't instantiate abstract class TestBroker with abstract method subscribe",
    ):
        TestBroker()
