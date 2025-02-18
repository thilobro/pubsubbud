import uuid


def create_header(channel: str) -> dict[str, str]:
    header = {}
    header["message_id"] = str(uuid.uuid4())
    header["channel"] = channel
    return header
