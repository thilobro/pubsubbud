import argparse
import asyncio
import curses
import json
import uuid

from websockets.asyncio.client import connect


class CLIChatClient:
    def __init__(self, name, host, port):
        self._host = host
        self._port = port
        self._current_room = "lobby"
        self._history = ""
        self._char_buffer = ""
        self._name = name

    def _add_to_buffer(self, line):
        self._history += line + "\n"

    def _show_buffer(self, char_buffer, stdscr):
        max_y, max_x = stdscr.getmaxyx()
        stdscr.clear()
        lines = self._history.splitlines()
        available_lines = max_y - 2
        if len(lines) > available_lines:
            lines = lines[-available_lines:]
        for line in lines:
            stdscr.addstr(line + "\n")
        stdscr.addstr(f"({self._current_room}) > {char_buffer}")
        stdscr.refresh()

    async def _process_command(self, command, connection):
        verb, obj = command.split(" ")
        if verb == "join":
            await self._join_room(obj, connection)

    async def _join_room(self, room_name, connection):
        await self._send_unsub_message(f"room.{self._current_room}", connection)
        await self._send_sub_message(f"room.{room_name}", connection)
        self._current_room = room_name

    async def _update_screen(self, stdscr, connection):
        char = stdscr.getch()
        if char == curses.ERR:
            return
        elif char == 10:
            if self._char_buffer:
                if self._char_buffer and self._char_buffer[0] == ":":
                    await self._process_command(self._char_buffer[1:], connection)
                else:
                    await self._send_chat_message(self._char_buffer, connection)
                self._char_buffer = ""
        elif char == 263:
            self._char_buffer = self._char_buffer[:-1]
        else:
            self._char_buffer = self._char_buffer + chr(char)
        self._show_buffer(self._char_buffer, stdscr)

    async def _read_console(self, stdscr, connection):
        stdscr.nodelay(True)
        self._show_buffer(self._char_buffer, stdscr)
        while True:
            await self._update_screen(stdscr, connection)
            await asyncio.sleep(0.001)

    async def _send_sub_message(self, channel_name, connection):
        sub_msg = {
            "header": {
                "message_id": str(uuid.uuid4),
                "channel": "subscription",
            },
            "content": {
                "subscription_type": "subscription",
                "subscription_channel": channel_name,
            },
        }
        await connection.send(json.dumps(sub_msg))

    async def _send_unsub_message(self, channel_name, connection):
        sub_msg = {
            "header": {
                "message_id": str(uuid.uuid4),
                "channel": "subscription",
            },
            "content": {
                "subscription_type": "unsubscription",
                "subscription_channel": channel_name,
            },
        }
        await connection.send(json.dumps(sub_msg))

    async def _handle_messages(self, stdscr, connection):
        await self._send_sub_message(f"room.{self._current_room}", connection)
        async for message in connection:
            message = json.loads(message)
            if "ack_id" not in message["header"].keys():
                name = message["content"]["from"]
                if name == self._name:
                    name = name + " (You)"
                message = (
                    f"({self._current_room}) > {name}: {message['content']['message']}"
                )
                self._add_to_buffer(message)
                self._show_buffer(self._char_buffer, stdscr)

    async def _send_chat_message(self, message, connection):
        room_msg = {
            "header": {"message_id": "0", "channel": f"room.{self._current_room}"},
            "content": {"message": message, "from": self._name},
        }
        await connection.send(json.dumps(room_msg))

    async def _run(self, stdscr):
        async with connect(f"ws://{self._host}:{self._port}") as connection:
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self._read_console(stdscr, connection))
                    tg.create_task(self._handle_messages(stdscr, connection))
            except KeyboardInterrupt:
                print("\nExiting...")

    def _curses_wrapper(self, stdscr):
        # Clear screen
        stdscr.clear()

        # Turn off echoing and enable cbreak mode
        curses.noecho()
        curses.cbreak()

        asyncio.run(self._run(stdscr))

    def run(self):
        curses.wrapper(self._curses_wrapper)


def get_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="CLI Chat Client",
        description="Chat in your terminal.",
        epilog="",
    )
    parser.add_argument("-p", "--port", default="8765")
    parser.add_argument("--host", default="localhost")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_cli_args()
    name = input("Enter your name: ")
    chat = CLIChatClient(name, args.host, args.port)
    chat.run()
