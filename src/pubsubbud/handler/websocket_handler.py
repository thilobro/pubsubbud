import asyncio
import json
import logging
from typing import Any, Optional

import websockets
from websockets.asyncio.server import serve

from pubsubbud.config import WebsocketHandlerConfig
from pubsubbud.handler.handler_interface import HandlerConnectionError, HandlerInterface
from pubsubbud.models import BrokerMessage


class WebsocketConnection:
    """Represents a WebSocket connection with a client.

    This class manages a single WebSocket connection, providing methods
    to send messages to the connected client.

    Attributes:
        _logger: Logger instance for logging messages
        _websocket: The underlying WebSocket connection
        _id: Unique identifier for the connection
    """

    def __init__(
        self, websocket: websockets.ServerConnection, logger: logging.Logger
    ) -> None:
        """Initialize a WebSocket connection.

        Args:
            websocket: The WebSocket connection to manage
            logger: Logger instance for logging messages
        """
        self._logger = logger
        self._websocket = websocket
        self._id = self._websocket.id

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message to the connected client.

        Args:
            message: The message to send, will be JSON serialized
        """
        await self._websocket.send(json.dumps(message))


class WebsocketHandler(HandlerInterface):
    """WebSocket implementation of the handler interface.

    This class implements the HandlerInterface using WebSockets for
    real-time bidirectional communication with clients.

    Attributes:
        _config: Configuration for the WebSocket server
        _run_task: Task running the WebSocket server
        _active_connections: Dictionary mapping connection IDs to WebSocket connections
    """

    def __init__(
        self,
        name: str,
        config: WebsocketHandlerConfig,
        logger: logging.Logger,
    ) -> None:
        """Initialize the WebSocket handler.

        Args:
            name: Name of the handler
            config: Configuration for the WebSocket server
            logger: Logger instance for logging messages
        """
        super().__init__(name=name, publish_callback=self._send, logger=logger)
        self._config = config
        self._run_task: Optional[asyncio.Task] = None
        self._active_connections: dict[str, WebsocketConnection] = {}

    async def _serve(self) -> None:
        """Start the WebSocket server and handle incoming connections."""
        async with serve(
            self._handle_websocket, self._config.host, self._config.port
        ) as server:
            await server.serve_forever()

    def run(self) -> None:
        """Start the WebSocket server in a background task."""
        self._run_task = asyncio.create_task(self._serve())

    async def stop(self) -> None:
        """Stop the WebSocket server and clean up resources."""
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.exceptions.CancelledError:
                self._logger.info(f"Interface {self._name} stopped.")

    async def _handle_websocket(self, websocket: websockets.ServerConnection) -> None:
        """Handle a new WebSocket connection.

        Args:
            websocket: The new WebSocket connection

        This method:
        1. Registers the connection
        2. Listens for incoming messages
        3. Processes messages and adds them to the message queue
        4. Handles connection closure
        """
        try:
            self._connect(websocket)
            async for message in websocket:
                # Ensure message is properly decoded if it's bytes
                message_str = (
                    message.decode() if isinstance(message, bytes) else message
                )
                message_dict = json.loads(message_str)
                message_dict["header"]["origin_id"] = str(websocket.id)
                self._logger.info(f"Message received: {message_dict}")
                await self._message_queue.put(BrokerMessage(**message_dict))
        except (
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
        ):
            self._logger.error("Error in websocket handler.", exc_info=True)
        finally:
            self._disconnect(websocket)

    async def _send(
        self, handler_id: str, content: dict[str, Any], header: dict[str, Any]
    ) -> None:
        """Send a message to a specific WebSocket client.

        Args:
            handler_id: ID of the WebSocket connection to send to
            content: Message content
            header: Message header

        Raises:
            HandlerConnectionError: If the specified connection is not found
        """
        try:
            connection = self._active_connections[handler_id]
        except KeyError:
            raise HandlerConnectionError(f"WebSocket {handler_id} not found")

        message = {"content": content, "header": header}
        await connection.send(message)

    def _connect(self, websocket: websockets.ServerConnection) -> None:
        """Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to register
        """
        self._active_connections[str(websocket.id)] = WebsocketConnection(
            websocket, self._logger
        )

    def _disconnect(self, websocket: websockets.ServerConnection) -> None:
        """Unregister a WebSocket connection.

        Args:
            websocket: The WebSocket connection to unregister
        """
        del self._active_connections[str(websocket.id)]
        self.unsubscribe(handler_id=str(websocket.id))

    async def _handle_connection_error(self, handler_id: str) -> bool:
        """Handle a connection error for a specific WebSocket.

        Args:
            handler_id: ID of the WebSocket connection that had an error

        Returns:
            bool: Always returns False to indicate the connection should be closed
        """
        self._logger.warning(f"WebSocket connection {handler_id} lost.")
        return False
