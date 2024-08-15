import redis
import docker

class RedisService:
    def __init__(self):
        self._container_redis_name = "redis_conf"
        self.docker_service = docker.from_env()
        self._r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def save_conf(self, key, value):
        """
        Save a configuration value to Redis.
        
        :param key: The configuration key.
        :param value: The value to store.
        """
        try:
            self._r.set(key, value)
            print(f"Configuration '{key}' saved with value: {value}")
        except redis.RedisError as e:
            print(f"Failed to save configuration '{key}': {e}")

    @property
    def conf(self):
        """
        Retrieve all configuration values from Redis.
        
        :return: A dictionary of all configuration keys and values.
        """
        try:
            return {key: self._r.get(key) for key in self._r.keys()}
        except redis.RedisError as e:
            print(f"Failed to retrieve configurations: {e}")
            return {}

if __name__ == "__main__":
    redis_service = RedisService()
    
    # Example: Save a configuration
    redis_service.save_conf('example_key', 'example_value')
    
    # Example: Retrieve all configurations
    config = redis_service.conf
    print("Current configurations:", config)


