"""
Example demonstrating MQTT client integration with pubsubbud.

This script shows how to:
1. Create a subscription message for the pubsub system
2. Connect to an MQTT broker
3. Subscribe to a unique topic using timestamp as UUID
4. Publish messages and receive responses

Requirements:
- Running MQTT broker on localhost:1883
- aiomqtt package installed

Usage:
    python test_mqtt_client.py
"""

import asyncio
import json
import time

from aiomqtt import Client


async def main():
    test_sub_msg = {
        "header": {
            "message_id": "1",
            "channel": "subscription",
        },
        "content": {
            "subscription_type": "subscription",
            "subscription_channel": "test",
        },
    }
    sub_topic = "mqtt/from_pubsub"
    pub_topic = "mqtt/to_pubsub"
    mqtt_client = Client("localhost", port=1883)
    uuid = str(time.time())
    sub_topic = sub_topic + "/" + uuid

    async with mqtt_client as client:
        test_sub_msg["header"]["origin_id"] = uuid
        await mqtt_client.subscribe(sub_topic)
        await client.publish(pub_topic, payload=json.dumps(test_sub_msg))
        async for message in client.messages:
            print(message.payload.decode())


asyncio.run(main())
