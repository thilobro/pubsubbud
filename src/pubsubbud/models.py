from typing import Any

import pydantic


class BrokerMessageHeader(pydantic.BaseModel):
    message_id: str
    channel: str
    origin_id: str


class BrokerMessage(pydantic.BaseModel):
    header: BrokerMessageHeader
    content: dict[str, Any]
