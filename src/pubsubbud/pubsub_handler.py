import redis.asyncio as redis
import asyncio
import threading
from typing import Callable, Any, Coroutine


AsyncCallback = Callable[[Any], Coroutine[Any, Any, Any]]


class PubsubHandler:

    def __init__(self):
        self._pubsub = redis.Redis().pubsub()
        self._setup_message_thread()
        self._canceled_event = asyncio.Event()
        self._callbacks: dict[str, AsyncCallback] = {}

    async def sub_channel(self, channel_name: str, callback: AsyncCallback) -> None:
        await self._pubsub.subscribe(channel_name)

    def unsub_channel(self, channel_name: str) -> None:
        pass

    def _setup_message_thread(self) -> None:
        def target() -> None:
            asyncio.run(self._run())

        self._message_thread = threading.Thread(target=target)

    def run(self) -> None:
        self._message_thread.start()

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
            if message:
                print(message)
        raise asyncio.CancelledError()

    def close(self) -> None:
        print("Closing pubsub.")
        self._canceled_event.set()
        self._message_thread.join()

    @property
    def is_running(self) -> bool:
        return not self._canceled_event.is_set()
