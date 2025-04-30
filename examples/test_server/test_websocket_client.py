"""
Example demonstrating WebSocket client interaction with pubsubbud.

This script shows how to:
1. Connect to a WebSocket server
2. Send different types of messages:
   - Regular message on 'test' channel
   - Subscription request
   - Unsubscription request
3. Receive and print responses
4. Handle WebSocket connection lifecycle

Requirements:
- Running pubsubbud WebSocket server on localhost:8765
- websockets package installed

Usage:
    python test_websocket_client.py
"""

import asyncio
import json
import os

from websockets.asyncio.client import connect

# Get host and port from environment variables or use defaults
HOST = os.getenv("WEBSOCKET_HOST", "localhost")
PORT = os.getenv("WEBSOCKET_PORT", "8765")
WS_URL = f"ws://{HOST}:{PORT}"

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
    print(f"Connecting to WebSocket server at {WS_URL}")
    async with connect(WS_URL) as websocket:
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
