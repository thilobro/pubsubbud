from typing import Callable, Any, Coroutine, Optional
from pubsubbud.pubsub_interface import PubsubInterface

AsyncCallback = Callable[[Any], Coroutine[Any, Any, Any]]


class CallbackHandler(PubsubInterface):
    def __init__(self) -> None:
        super().__init__(publish_callback=self._execute_callbacks)
        self._callbacks: dict[str, AsyncCallback] = {}

    async def _execute_callbacks(self, interface_id: str,
                                 content: dict[str, Any], header: dict[str, Any]):
        callbacks = self._callbacks[interface_id]
        for callback in callbacks:
            await callback(content, header)

    def run(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def register_callback(self, interface_id: str, callback: AsyncCallback) -> None:
        try:
            self._callbacks[interface_id].append(callback)
        except KeyError:
            self._callbacks[interface_id] = [callback]

    def unregister_calback(self, interface_id: str, callback: Optional[AsyncCallback]) -> None:
        try:
            if callback:
                self._callbacks[interface_id].pop(callback)
                if not self._callbacks[interface_id]:
                    del self._callbacks[interface_id]
            else:
                del self._callbacks[interface_id]
        except KeyError:
            print(f"Unable to unregister callbacks to interface id {interface_id}")
