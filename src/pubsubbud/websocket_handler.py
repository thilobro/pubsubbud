import websockets
import asyncio
import json
from websockets.asyncio.server import serve
from typing import Callable, Any, Coroutine, Optional
from pubsubbud.pubsub_interface import PubsubInterface

AsyncCallback = Callable[[Any], Coroutine[Any, Any, Any]]


class WebsocketConnection:
    def __init__(self, websocket: websockets.ServerConnection) -> None:
        self._websocket = websocket

    async def send(self, message) -> None:
        await self._websocket.send(message)


class WebsocketHandler(PubsubInterface):

    def __init__(self, process_message_callback: AsyncCallback) -> None:
        super().__init__(publish_callback=self._send)
        self._run_task: Optional[asyncio.Task] = None
        self._active_connections: dict[str, WebsocketConnection] = {}
        self._process_message_callback = process_message_callback

    async def _serve(self) -> None:
        async with serve(self._handle_websocket, "localhost", 8765) as server:
            await server.serve_forever()

    def run(self) -> None:
        self._run_task = asyncio.create_task(self._serve())

    async def stop(self) -> None:
        self._run_task.cancel()
        await self._run_task

    async def _handle_websocket(self, websocket) -> None:
        try:
            self._connect(websocket)
            self._active_connections[websocket.id]
            async for message in websocket:
                message = json.loads(message)
                channel = message["channel"]
                data = message["data"]
                print(f"Message received: {message}")
                await self._process_message_callback(channel, data, internal=True)
        except (websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK):
            print("ERROR in websocket")
        finally:
            self._disconnect(websocket)

    async def _send(self, interface_id: str,
                    content: dict[str, Any], header: dict[str, Any]) -> None:
        message = {"content": content, "header": header}
        self._active_connections[interface_id].send(message)

    def _connect(self, websocket) -> None:
        self._active_connections[websocket.id] = WebsocketConnection(websocket)

    def _disconnect(self, websocket) -> None:
        del self._active_connections[websocket.id]
