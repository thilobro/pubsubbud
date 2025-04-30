"""
Example demonstrating basic Kafka producer and consumer setup with pubsubbud.

This script shows how to:
1. Create a subscription message for the pubsub system
2. Set up an async Kafka producer and consumer
3. Send a message to a Kafka topic

Requirements:
- Running Kafka broker on localhost:9092
- aiokafka package installed

Usage:
    python test_kafka.py
    or
    KAFKA_HOST=localhost KAFKA_PORT=9092 python test_kafka.py
"""

import asyncio
import json
import os
import sys

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

# Get host and port from environment variables or use defaults
KAFKA_HOST = os.getenv("KAFKA_HOST", "localhost")
KAFKA_PORT = os.getenv("KAFKA_PORT", "9092")
KAFKA_BOOTSTRAP_SERVERS = f"{KAFKA_HOST}:{KAFKA_PORT}"

test_sub_msg = {
    "header": {
        "message_id": "1",
        "channel": "subscription",
        "origin_id": "test_origin",
    },
    "content": {
        "subscription_type": "subscription",
        "subscription_channel": "test",
    },
}


async def main():
    pub_topic = "kafka.to_pubsub"
    print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")

    try:
        consumer = AIOKafkaConsumer(
            bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
            client_id="test_client",
            group_id="test_group",
        )
        producer = AIOKafkaProducer(
            bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS], client_id="test_producer"
        )

        print("Starting consumer...")
        await consumer.start()
        print("Starting producer...")
        await producer.start()

        print(f"Sending message to topic {pub_topic}")
        await producer.send_and_wait(pub_topic, json.dumps(test_sub_msg).encode("utf"))
        print("Message sent successfully")

        await consumer.stop()
        await producer.stop()

    except KafkaConnectionError as e:
        print(f"Failed to connect to Kafka: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
