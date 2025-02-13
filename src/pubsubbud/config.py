import json

import pydantic


class JsonConfig(pydantic.BaseModel):
    @classmethod
    def from_json(cls, json_path):
        with open(json_path) as f:
            json_config = json.load(f)
        return cls.model_validate(json_config)


class PubsubHandlerConfig(JsonConfig):
    uuid: str


class WebsocketHandlerConfig(JsonConfig):
    host: str
    port: int
