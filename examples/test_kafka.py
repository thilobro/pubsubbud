import asyncio
import json

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

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
    consumer = AIOKafkaConsumer(bootstrap_servers=["localhost:9092"])
    producer = AIOKafkaProducer(bootstrap_servers=["localhost:9092"])
    await consumer.start()
    await producer.start()
    await producer.send_and_wait(pub_topic, json.dumps(test_sub_msg).encode("utf"))
    await consumer.stop()
    await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
