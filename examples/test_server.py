from pubsubbud import pubsub_handler, callback_handler, websocket_handler
import asyncio
from typing import Any


async def callback(content: dict[str, Any], header: dict[str, Any]) -> None:
    print("Executed callback")
    print(content)
    print(header)


async def callback2(content: dict[str, Any], header: dict[str, Any]) -> None:
    print("Executed callback2")
    print(content)
    print(header)


async def main() -> None:
    ps_handler = pubsub_handler.PubsubHandler("123")

    cb_handler = callback_handler.CallbackHandler()
    cb_handler.register_callback("test_callback", callback)
    cb_handler.register_callback("test_callback", callback2)

    ws_handler = websocket_handler.WebsocketHandler(ps_handler.publish,
                                                    ps_handler.subscribe,
                                                    ps_handler.unsubscribe)

    ps_handler.add_interface("callback", cb_handler)
    ps_handler.add_interface("websocket", ws_handler)
    await ps_handler.subscribe(channel_name="test",
                               interface_name="callback",
                               interface_id="test_callback")
    await ps_handler.publish("test", {"test": 1})
    ps_handler.run()
    while True:
        await asyncio.sleep(5)
        await ps_handler.publish("test", {"test": 1})
    # ps_handler.close()


asyncio.run(main())
