import asyncio
import json

from websockets.asyncio.client import connect

test_msg = {"type": "pubsub", "channel": "test", "data": "test2"}
test_sub_msg = {
    "type": "subscription",
    "subscription_type": "subscription",
    "subscription_channel": "test",
}
test_unsub_msg = {
    "type": "subscription",
    "subscription_type": "unsubscription",
    "subscription_channel": "test",
}


async def hello():
    async with connect("ws://localhost:8765") as websocket:
        await websocket.send(json.dumps(test_msg))
        await websocket.send(json.dumps(test_sub_msg))
        i = 0
        for i in range(3):
            message = await websocket.recv()
            print(message)
            i += 1
        await websocket.send(json.dumps(test_unsub_msg))
        while True:
            message = await websocket.recv()
            print(message)


if __name__ == "__main__":
    asyncio.run(hello())
