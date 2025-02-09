import asyncio
from websockets.asyncio.client import connect
import json

test_msg = {"channel": "test", "data": "test2"}


async def hello():
    async with connect("ws://localhost:8765") as websocket:
        await websocket.send(json.dumps(test_msg))
        message = await websocket.recv()
        print(message)


if __name__ == "__main__":
    asyncio.run(hello())
