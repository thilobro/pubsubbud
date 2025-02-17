import asyncio
import json

from aiomqtt import Client


async def main():
    test_msg = {
        "header": {"message_id": "0", "channel": "test"},
        "content": {"test": "test_mqtt"},
    }
    sub_topic = "mqtt/from_pubsub"
    pub_topic = "mqtt/to_pubsub"
    mqtt_client = Client("localhost", port=1883)

    async with mqtt_client as client:
        await mqtt_client.subscribe(sub_topic)
        await client.publish(pub_topic, payload=json.dumps(test_msg))
        async for message in client.messages:
            print(message.payload)


asyncio.run(main())
