import asyncio
import logging
import os
from typing import Any

import duckdb

from pubsubbud.broker.redis_broker import RedisBroker
from pubsubbud.config import (
    RedisBrokerConfig,
    WebsocketHandlerConfig,
)
from pubsubbud.handler import websocket_handler
from pubsubbud.helpers import create_header
from pubsubbud.pubsub_manager import PubsubManager

BROKER = os.environ.get("BROKER", "redis")


class DuckDBHistoryLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        # Use file-based database in a mounted directory
        self._db = duckdb.connect("/data/chat_history.db")
        try:
            # Create table if it doesn't exist
            self._db.sql(
                "create table if not exists history (timestamp float, room string, sender string, message string);"
            )
        except Exception as e:
            self._logger.error(f"Error creating history table: {e}", exc_info=True)

    def log(self, message: str, timestamp: float, room: str, sender: str) -> None:
        try:
            self._db.sql(
                f"insert into history (timestamp, room, sender, message) values ({timestamp}, '{room}', '{sender}', '{message}');"
            )
        except Exception as e:
            self._logger.error(f"Error logging history: {e}", exc_info=True)

    def get_room_history(self, room: str) -> list[dict]:
        history = self._db.sql(
            f"select timestamp, room, sender, message from history where room = '{room}'"
        ).fetchall()

        history_list = [
            {
                "timestamp": float(row[0]),
                "room": str(row[1]),
                "sender": str(row[2]),
                "message": str(row[3]),
            }
            for row in history
        ]
        return history_list


class CLIChatServer:
    def __init__(self, logger, history_logger):
        self._logger = logger
        self._history_logger = history_logger
        if BROKER == "redis":
            redis_broker_config_path = "./configs/redis_broker.json"
            config = RedisBrokerConfig.from_json(redis_broker_config_path)
            broker = RedisBroker(config)
        else:
            raise ValueError(f"Unknown broker: {BROKER}")
        self._ps_manager = PubsubManager(broker=broker, logger=logger)

        websocket_handler_config_path = "./configs/websocket_handler.json"
        ws_handler_config = WebsocketHandlerConfig.from_json(
            websocket_handler_config_path
        )
        ws_handler = websocket_handler.WebsocketHandler(
            "websocket",
            ws_handler_config,
            logger,
        )

        self._ps_manager.add_handler(ws_handler)

    async def _start_callback_recording(self) -> None:
        async def record_history_callback(
            content: dict[str, Any], header: dict[str, Any]
        ) -> None:
            message = content["message"]
            sender = content["from"]
            room = header["channel"].replace("room.", "")
            timestamp = header["timestamp"]
            self._history_logger.log(
                message=message, sender=sender, room=room, timestamp=timestamp
            )

        async def send_history_callback(
            content: dict[str, Any], header: dict[str, Any]
        ) -> None:
            room = content["room"]
            handler_id = header["origin_id"]
            channel = "history_reply"
            history = self._history_logger.get_room_history(room)
            await self._ps_manager.forward_to_handlers(
                channel=channel,
                content={"history": history},
                header=create_header(channel),
                handler_id=handler_id,
                handler_type="websocket",
            )

        await self._ps_manager.register_callback("room.*", record_history_callback)
        await self._ps_manager.register_callback(
            "history_request", send_history_callback
        )

    async def run(self):
        await self._start_callback_recording()
        self._ps_manager.run()


async def main():
    logger = logging.getLogger("test_logger")
    history_logger = DuckDBHistoryLogger(logger)
    logging.basicConfig(level=logging.INFO)
    chat_server = CLIChatServer(logger, history_logger)

    await chat_server.run()
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
