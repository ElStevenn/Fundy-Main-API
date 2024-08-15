import redis

class RedisService():
    def __init__(self) -> None:
        self._r = redis.Redis(host='localhost', port)

