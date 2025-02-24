# PubsubBud

PubsubBud is a modular publish subscribe framework.
It provides an easy way to communicate consistently between multiple frontend clients and backend replicas.
It handles communication between different handlers by using a single message broker.
Work in progress.

## Brokers

Only one message broker can be used at a time.
Available brokers:
* Redis
* MQTT
New brokers can be added by implementing the `BrokerInterface` abstract base class.

## Handlers

Multiple handlers can be used at the same time.
Available handlers:
* websockets
* MQTT
New handlers can be added by implementing the `HandlerInterface` abstract base class.
