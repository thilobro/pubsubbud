import time
import uuid
from typing import Any


def get_current_timestamp() -> float:
    """Get the current Unix timestamp.

    Returns:
        float: Current time as a Unix timestamp (seconds since epoch).
    """
    return time.time()


def create_header(channel: str, origin_id: str = "pubsub") -> dict[str, Any]:
    """Create a message header with metadata.

    Args:
        channel: The channel the message is published to.
        origin_id: Identifier of the message sender. Defaults to "pubsub".

    Returns:
        dict[str, Any]: A dictionary containing message metadata including:
            - message_id: A unique UUID for the message
            - channel: The target channel
            - origin_id: The sender's identifier
            - timestamp: Current Unix timestamp
    """
    header: dict[str, Any] = {}
    header["message_id"] = str(uuid.uuid4())
    header["channel"] = channel
    header["origin_id"] = origin_id
    header["timestamp"] = get_current_timestamp()
    return header
