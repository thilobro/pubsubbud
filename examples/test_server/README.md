# Test Server Example

This example demonstrates a complete server setup with support for multiple message brokers and protocol handlers. It's designed to showcase the flexibility and power of the pubsubbud library in a real-world scenario.

## Features

- Multiple broker support:
  - Redis
  - MQTT
  - Kafka
- Multiple protocol handlers:
  - WebSocket
  - MQTT
  - Kafka
- Docker Compose setup for all brokers
- Environment-based configuration
- Example clients for each protocol

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Poetry for Python dependency management

## Quick Start

1. Start all brokers using Docker Compose:

```bash
docker compose up
```

This will start:
- Redis server on port 6379
- MQTT broker on port 1883 (with WebSocket interface on port 9001)
- Kafka broker on port 9092 (with Zookeeper on port 2181)

2. Start the test server:

```bash
poetry run python test_server.py
```

3. In a separate terminal, run one of the example clients:

```bash
# WebSocket client
poetry run python test_websocket_client.py

# MQTT client
poetry run python test_mqtt_client.py

# Kafka client
poetry run python test_kafka_client.py
```

## Configuration

The server and clients are configured through environment variables and configuration files:

- `BROKER_TYPE`: Choose between "redis", "mqtt", or "kafka" (default: "redis")

For the test server, broker configuration is handled through JSON files in the `configs/` directory:
- `redis_broker.json`: Redis broker configuration
- `mqtt_handler.json`: MQTT handler configuration
- `kafka_handler.json`: Kafka handler configuration

For the example clients:
- WebSocket client: `WEBSOCKET_HOST` and `WEBSOCKET_PORT` (default: localhost:8765)
- Kafka client: `KAFKA_HOST` and `KAFKA_PORT` (default: localhost:9092)
- MQTT client: Currently hardcoded to localhost:1883

## Docker Compose Setup

The `docker-compose.yml` file sets up all required brokers in a single environment:

- **Redis**
  - Port: 6379
  - Simple and lightweight option
  - Good for development and testing

- **MQTT (Mosquitto)**
  - MQTT port: 1883
  - WebSocket interface: 9001
  - Suitable for IoT and real-time applications

- **Kafka**
  - Zookeeper: 2181
  - Kafka broker: 9092
  - Ideal for high-throughput, distributed systems

## Example Clients

### WebSocket Client
- Connects to the server's WebSocket endpoint
- Demonstrates subscription and message publishing
- Supports both regular and subscription messages

### MQTT Client
- Connects directly to the MQTT broker
- Shows how to handle MQTT-specific features
- Includes topic subscription and message publishing

### Kafka Client
- Demonstrates Kafka producer and consumer setup
- Shows how to handle Kafka-specific message formats
- Includes topic management and message publishing

## Troubleshooting

1. **Connection Issues**
   - Ensure the broker is running and accessible
   - Check the broker host and port configuration
   - Verify network connectivity between components

2. **Message Delivery Problems**
   - Check topic names and prefixes
   - Verify subscription status
   - Monitor broker logs for errors

3. **Docker Issues**
   - Ensure ports are not already in use
   - Check Docker service status
   - Review Docker Compose logs

## Contributing

Feel free to submit issues and enhancement requests! 