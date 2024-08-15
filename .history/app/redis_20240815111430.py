import redis
import docker

class RedisService():
    def __init__(self):
        self._container_redis_name = "redis_conf"
        self.docker_service = docker.from_env()
        self._r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
    def save_conf(self):
        pass

    def conf():
        pass

if __name__ == "__main__":
    pass