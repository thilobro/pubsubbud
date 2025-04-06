# Pubsubbud Examples

This directory contains various examples demonstrating different aspects and use cases of the pubsubbud library.

## Quick Examples

### `test_kafka.py`
Demonstrates basic Kafka integration with pubsubbud:
- Setting up async Kafka producer and consumer
- Creating subscription messages
- Sending messages to Kafka topics

### `test_mqtt_client.py`
Shows MQTT client integration:
- Connecting to an MQTT broker
- Subscribing to topics with unique IDs
- Publishing and receiving messages

### `test_websocket_client.py`
Illustrates WebSocket client functionality:
- Connecting to a WebSocket server
- Sending different message types (regular, subscription, unsubscription)
- Handling message responses

### `test_server.py`
Provides a complete server setup example:
- Configurable broker selection (Redis, MQTT, Kafka)
- Multiple protocol handler integration
- Callback registration
- Message publishing

## Complete Application Example

### `cli_chat/`
A full-featured command-line chat application demonstrating real-world usage:
- Multi-room chat system
- WebSocket-based communication
- Redis message broker
- Docker deployment support
- Curses-based UI

See the [CLI Chat README](cli_chat/README.md) for detailed information about this example.

## Running the Examples

Each example has specific requirements and setup instructions documented in its header comments. Generally, you'll need:

1. Required broker running locally (Redis/MQTT/Kafka depending on example)
2. Appropriate configuration files in the `configs/` directory
3. Dependencies installed via Poetry

Example:
```bash
# For Kafka example
poetry run python test_kafka.py

# For MQTT example
poetry run python test_mqtt_client.py

# For WebSocket example
poetry run python test_websocket_client.py

# For complete server example
poetry run python test_server.py
```

## Configuration

Configuration files for all examples are stored in the `configs/` directory. Make sure to review and adjust these configurations according to your environment. 