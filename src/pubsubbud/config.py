import json

import pydantic


class JsonConfig(pydantic.BaseModel):
    @classmethod
    def from_json(cls, json_path):
        with open(json_path) as f:
            json_config = json.load(f)
        return cls.model_validate(json_config)


class PubsubManagerConfig(JsonConfig):
    uuid: str


class WebsocketHandlerConfig(JsonConfig):
    host: str
    port: int


class MqttHandlerConfig(JsonConfig):
    host: str
    port: int
    to_pubsub_topic: str
    from_pubsub_topic: str


class RedisBrokerConfig(JsonConfig):
    host: str
    port: int


class MqttBrokerConfig(JsonConfig):
    host: str
    port: int
