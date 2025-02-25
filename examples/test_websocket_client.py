import asyncio
import json

from websockets.asyncio.client import connect

test_msg = {
    "header": {"message_id": "0", "channel": "test"},
    "content": {"test": "test2"},
}
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

test_unsub_msg = {
    "header": {
        "message_id": "2",
        "channel": "subscription",
    },
    "content": {
        "subscription_type": "unsubscription",
        "subscription_channel": "test",
    },
}


async def hello():
    async with connect("ws://localhost:8765") as websocket:
        test_msg["header"]["origin_id"] = str(websocket.id)
        test_sub_msg["header"]["origin_id"] = str(websocket.id)
        test_unsub_msg["header"]["origin_id"] = str(websocket.id)
        await websocket.send(json.dumps(test_msg))
        await websocket.send(json.dumps(test_sub_msg))
        i = 0
        for i in range(10):
            message = await websocket.recv()
            print(message)
            i += 1
        await websocket.send(json.dumps(test_unsub_msg))
        while True:
            message = await websocket.recv()
            print(message)


if __name__ == "__main__":
    asyncio.run(hello())
