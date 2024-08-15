import redis
import docker

class RedisService():
    def __init__(self):
        self.docker_service = client = docker.from_env()
        self._r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
