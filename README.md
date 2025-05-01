# PubsubBud

PubsubBud is a modular publish-subscribe framework that simplifies communication between frontend clients and backend replicas. It provides a unified messaging interface by abstracting different message brokers and communication protocols into a single, consistent API.

## Features

- Single message broker architecture for consistent message delivery
- Multiple protocol handlers for client communication
- Pattern-based message subscription support
- Modular design for easy extension
- Async/await support
- Automatic channel management

## Installation

```bash
poetry install
```

## Message Brokers

PubsubBud uses a single message broker for all communication. Currently supported brokers:

- **Redis**: Fast, in-memory message broker
- **MQTT**: Lightweight messaging for IoT devices
- **Kafka**: Distributed streaming platform

Implement the `BrokerInterface` to add support for additional message brokers:

```python
from pubsubbud.broker.broker_interface import BrokerInterface

class CustomBroker(BrokerInterface):
    async def subscribe(self, channel_name: str) -> None:
        ...
```

## Protocol Handlers

Multiple handlers can be used simultaneously to support different client protocols:

- **WebSocket**: Real-time web client communication
- **MQTT**: IoT device communication
- **Kafka**: Distributed streaming platform

Add new handlers by implementing the `HandlerInterface`:

```python
from pubsubbud.handler.handler_interface import HandlerInterface

class CustomHandler(HandlerInterface):
    async def publish_if_subscribed(self, channel: str, content: dict, header: dict) -> None:
        ...
```

## Configuration

PubsubBud uses Pydantic models for configuration. Example configurations can be found in the `configs/` directory:

- `redis_broker.json`: Redis broker settings
- `mqtt_broker.json`: MQTT broker settings
- `kafka_broker.json`: Kafka broker settings

## Examples

### Pattern-Based Subscriptions

PubsubBud supports pattern matching for message subscriptions using shell-style wildcards:

```python
# Subscribe to all channels starting with "sensor."
async def temperature_callback(content: dict, header: dict):
    print(f"Temperature reading: {content['temperature']}")
    
await pubsub_manager.register_callback("sensor.*", temperature_callback)

# This will match channels like:
# - sensor.temperature
# - sensor.humidity
# - sensor.pressure
```

Pattern matching supports:
- `*`: Matches any sequence of characters
- `?`: Matches any single character
- `[seq]`: Matches any character in seq
- `[!seq]`: Matches any character not in seq

### Message Validation

PubsubBud supports content validation through validation callbacks. These callbacks can be used to ensure messages meet specific requirements before being processed:

```python
# Define a validation callback
def validate_temperature(content: dict) -> bool:
    # Ensure temperature is within valid range
    return -50 <= content.get('temperature', 0) <= 150

# Create a handler with validation
handler = WebsocketHandler(
    name="temperature_handler",
    config=config,
    logger=logger,
    content_validation_callback=validate_temperature
)

# Add handler to pubsub manager
pubsub_manager.add_handler(handler)

# Subscribe to temperature channel
handler.subscribe("temperature", "client1")

# Only messages with valid temperature values will be processed
# Invalid messages will be silently dropped
```

Validation callbacks can be used to:
- Validate data types and ranges
- Check required fields
- Enforce business rules
- Filter unwanted messages

Multiple handlers can have different validation rules for the same channel, allowing for protocol-specific validation requirements.

Check the `examples/` directory for:
- Basic usage examples
- Different broker configurations
- Possible client implementations
- Complete application examples

## Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run example
poetry run python examples/cli_chat/cli_chat_server.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## Project Status

This project is under active development. Features and APIs may change.
