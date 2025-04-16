import time
from typing import Any

import pydantic


class BrokerMessageHeader(pydantic.BaseModel):
    """Header information for a broker message.

    This class represents the metadata associated with a message in the pubsub system.
    It includes information about the message's origin, destination, and timing.

    Attributes:
        message_id: Unique identifier for the message.
        channel: The channel the message is published to.
        origin_id: Identifier of the message sender.
        timestamp: Unix timestamp of when the message was created. Defaults to current time.
    """

    message_id: str
    channel: str
    origin_id: str
    timestamp: float = pydantic.Field(default_factory=time.time)


class BrokerMessage(pydantic.BaseModel):
    """Complete message structure for the pubsub system.

    This class represents a complete message in the pubsub system, combining
    header metadata with the actual message content.

    Attributes:
        header: Metadata about the message (BrokerMessageHeader).
        content: The actual message payload as a dictionary.
    """

    header: BrokerMessageHeader
    content: dict[str, Any]
