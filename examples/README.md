# Pubsubbud Examples

This directory contains various examples demonstrating different aspects and use cases of the pubsubbud library.

## Examples

### `test_server/`
A complete server setup with Docker support:
- Configurable broker selection (Redis, MQTT, Kafka)
- Multiple protocol handler integration
- Docker Compose setup for all brokers
- WebSocket, MQTT, and Kafka client examples
- Environment-based configuration

See the [Test Server README](test_server/README.md) for detailed information about this example.

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
# For test server example
cd test_server
docker compose -f docker-compose.yml up

# For CLI chat example
cd cli_chat
docker compose up
```

## Configuration

Configuration files for all examples are stored in the `configs/` directory. Make sure to review and adjust these configurations according to your environment. 