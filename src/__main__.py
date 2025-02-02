from pubsubbud import pubsub_handler
import asyncio
from typing import Any


async def callback(message: Any) -> bool:
    print("Executed callback")
    return True


async def main() -> None:
    ps_handler = pubsub_handler.PubsubHandler()
    await ps_handler.sub_channel("test", callback)
    ps_handler.run()
    await asyncio.sleep(5)
    ps_handler.close()


asyncio.run(main())
