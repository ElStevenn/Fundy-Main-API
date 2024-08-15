import redis
import docker

class RedisService():
    def __init__(self):
        self.docker_service = docker.from_env()
        self._r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        


if __name__ == "__main__":
    pass