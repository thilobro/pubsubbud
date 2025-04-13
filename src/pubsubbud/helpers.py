import time
import uuid
from typing import Any


def get_current_timestamp() -> float:
    return time.time()


def create_header(channel: str, origin_id: str = "pubsub") -> dict[str, Any]:
    header: dict[str, Any] = {}
    header["message_id"] = str(uuid.uuid4())
    header["channel"] = channel
    header["origin_id"] = origin_id
    header["timestamp"] = get_current_timestamp()
    return header
