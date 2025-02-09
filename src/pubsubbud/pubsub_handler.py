import redis.asyncio as redis
import asyncio
import threading
from typing import Callable, Any, Coroutine
import uuid
import json
from pubsubbud.pubsub_interface import PubsubInterface


AsyncCallback = Callable[[Any], Coroutine[Any, Any, Any]]


def create_header(channel: str) -> dict[str, Any]:
    header = {}
    header["_id"] = str(uuid.uuid4())
    header["channel"] = channel
    return header


class PubsubHandler:

    def __init__(self, uuid: str) -> None:
        self._uuid = uuid
        self._redis = redis.Redis()
        self._pubsub = self._redis.pubsub()
        self._setup_message_thread()
        self._canceled_event = asyncio.Event()
        self._interfaces = {}

    async def subscribe(self, channel_name: str, interface_name: str, interface_id: str) -> None:
        self._interfaces[interface_name].subscribe(channel_name, interface_id)
        await self._pubsub.subscribe(channel_name)
        await self._pubsub.subscribe(f"{self._uuid}/{channel_name}")

    async def unsubscribe(self, channel_name: str, interface_name: str, interface_id: str) -> None:
        self._interfaces[interface_name].unsubscribe(interface_id)
        await self._pubsub.unsubscribe(channel_name)
        await self._pubsub.unsubscribe(f"{self._uuid}/{channel_name}")

    def _setup_message_thread(self) -> None:
        def target() -> None:
            asyncio.run(self._run())

        self._message_thread = threading.Thread(target=target)

    def _run_message_task(self) -> None:
        self._message_task = asyncio.create_task(self._read_messages())

    def _run_interface_tasks(self) -> None:
        for interface in self._interfaces.values():
            interface.run()

    def run(self) -> None:
        self._run_message_task()
        self._run_interface_tasks()

    async def _run(self) -> None:
        message_task = asyncio.create_task(self._read_messages())
        try:
            await message_task
        except asyncio.CancelledError:
            print("Pubsub cancelled.")
            if not message_task.cancelled():
                message_task.cancel()

    async def _read_messages(self) -> None:
        while not self._canceled_event.is_set():
            message = await self._pubsub.get_message()
            if message and not message["type"] == "subscribe":
                print(f"From redis: {message}")
                channel = message["channel"].decode()
                if "/" in channel:
                    channel = channel.split("/")[1]
                data = json.loads(message["data"].decode())
                content = data["content"]
                header = data["header"]
                await self._forward_to_interfaces(channel, content, header)
        raise asyncio.CancelledError()

    async def _forward_to_interfaces(self, channel, content, header) -> None:
        for interface in self._interfaces.values():
            await interface.publish_if_subscribed(channel, content, header)

    def add_interface(self, name: str, interface: PubsubInterface) -> None:
        self._interfaces[name] = interface

    def close(self) -> None:
        print("Closing pubsub.")
        self._canceled_event.set()

    async def publish(self, channel, data: dict[str, Any], internal=False) -> None:
        message = {}
        message["content"] = data
        message["header"] = create_header(channel)
        if internal:
            channel = f"{self._uuid}/{channel}"
        print(f"To redis: {message}, {channel}")
        await self._redis.publish(channel, json.dumps(message))

    @property
    def is_running(self) -> bool:
        return not self._canceled_event.is_set()
