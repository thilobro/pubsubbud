import logging
from typing import Any, Optional

from pubsubbud.custom_types import CBHandlerCallback
from pubsubbud.pubsub_interface import PubsubInterface


class CallbackHandler(PubsubInterface):
    def __init__(self, name: str, logger: logging.Logger) -> None:
        super().__init__(
            name=name, publish_callback=self._execute_callbacks, logger=logger
        )
        self._callbacks: dict[str, list[CBHandlerCallback]] = {}

    async def _execute_callbacks(
        self, interface_id: str, content: dict[str, Any], header: dict[str, Any]
    ):
        callbacks = self._callbacks[interface_id]
        for callback in callbacks:
            await callback(content, header)

    def run(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def _message_iterator(self) -> None:
        return None

    def register_callback(self, interface_id: str, callback: CBHandlerCallback) -> None:
        try:
            self._callbacks[interface_id].append(callback)
        except KeyError:
            self._callbacks[interface_id] = [callback]

    def unregister_calback(
        self, interface_id: str, callback: Optional[CBHandlerCallback]
    ) -> None:
        try:
            if callback:
                self._callbacks[interface_id].remove(callback)
                if not self._callbacks[interface_id]:
                    del self._callbacks[interface_id]
            else:
                del self._callbacks[interface_id]
        except KeyError:
            self._logger.warning(
                f"Unable to unregister callbacks to interface id {interface_id}"
            )
