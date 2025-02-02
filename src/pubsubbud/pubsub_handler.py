import redis


class PubsubHandler:

    def __init__(self):
        self._pubsub = redis.Redis().pubsub()
