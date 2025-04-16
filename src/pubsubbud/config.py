import json
from typing import Type, TypeVar

import pydantic

T = TypeVar("T", bound="JsonConfig")


class JsonConfig(pydantic.BaseModel):
    """Base class for JSON-based configuration models.

    This class provides functionality to load configuration from JSON files
    and validate the configuration against the model schema.
    """

    @classmethod
    def from_json(cls: Type[T], json_path: str) -> T:
        """Load configuration from a JSON file.

        Args:
            json_path: Path to the JSON configuration file.

        Returns:
            An instance of the configuration class with values loaded from the JSON file.

        Raises:
            FileNotFoundError: If the JSON file doesn't exist.
            ValidationError: If the JSON data doesn't match the model schema.
        """
        with open(json_path) as f:
            json_config = json.load(f)
        return cls.model_validate(json_config)


class PubsubManagerConfig(JsonConfig):
    """Configuration for the PubsubManager.

    Attributes:
        uuid: Unique identifier for the pubsub manager instance.
    """

    uuid: str


class WebsocketHandlerConfig(JsonConfig):
    """Configuration for the WebSocket handler.

    Attributes:
        host: Host address to bind the WebSocket server to.
        port: Port number to bind the WebSocket server to.
    """

    host: str
    port: int


class MqttHandlerConfig(JsonConfig):
    """Configuration for the MQTT handler.

    Attributes:
        host: MQTT broker host address.
        port: MQTT broker port number.
        to_pubsub_topic: Topic for messages from MQTT to pubsub.
        from_pubsub_topic: Topic for messages from pubsub to MQTT.
    """

    host: str
    port: int
    to_pubsub_topic: str
    from_pubsub_topic: str


class RedisBrokerConfig(JsonConfig):
    """Configuration for the Redis broker.

    Attributes:
        host: Redis server host address.
        port: Redis server port number.
    """

    host: str
    port: int


class MqttBrokerConfig(JsonConfig):
    """Configuration for the MQTT broker.

    Attributes:
        host: MQTT broker host address.
        port: MQTT broker port number.
    """

    host: str
    port: int


class KafkaBrokerConfig(JsonConfig):
    """Configuration for the Kafka broker.

    Attributes:
        host: Kafka broker host address.
        port: Kafka broker port number.
    """

    host: str
    port: int


class KafkaHandlerConfig(JsonConfig):
    """Configuration for the Kafka handler.

    Attributes:
        host: Kafka broker host address.
        port: Kafka broker port number.
        to_pubsub_topic: Topic for messages from Kafka to pubsub.
        from_pubsub_topic: Topic for messages from pubsub to Kafka.
        connection_retries: Number of times to retry connection on failure. Defaults to 3.
    """

    host: str
    port: int
    to_pubsub_topic: str
    from_pubsub_topic: str
    connection_retries: int = 3  # Default to 3 retries if not specified
