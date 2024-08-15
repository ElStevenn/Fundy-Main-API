
import docker
import redis
import json

class RedisService:
    def __init__(self):
        self._r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def save_task(self, task_id, task_data):
        """
        Save a task to Redis.
        
        :param task_id: The ID of the task.
        :param task_data: A dictionary containing the task details.
        """
        try:
            self._r.hset("tasks", task_id, json.dumps(task_data))
            print(f"Task '{task_id}' saved successfully.")
        except redis.RedisError as e:
            print(f"Failed to save task '{task_id}': {e}")

    def get_task(self, task_id):
        """
        Retrieve a task from Redis by its ID.
        
        :param task_id: The ID of the task.
        :return: A dictionary containing the task details, or None if not found.
        """
        try:
            task_data = self._r.hget("tasks", task_id)
            if task_data:
                return json.loads(task_data)
            else:
                print(f"Task '{task_id}' not found.")
                return None
        except redis.RedisError as e:
            print(f"Failed to retrieve task '{task_id}': {e}")
            return None

    def delete_task(self, task_id):
        """
        Delete a task from Redis.
        
        :param task_id: The ID of the task to delete.
        """
        try:
            result = self._r.hdel("tasks", task_id)
            if result:
                print(f"Task '{task_id}' deleted successfully.")
            else:
                print(f"Task '{task_id}' not found or could not be deleted.")
        except redis.RedisError as e:
            print(f"Failed to delete task '{task_id}': {e}")

    def get_all_tasks(self):
        """
        Retrieve all tasks from Redis.
        
        :return: A dictionary of all tasks, with task IDs as keys.
        """
        try:
            tasks = self._r.hgetall("tasks")
            return {task_id: json.loads(task_data) for task_id, task_data in tasks.items()}
        except redis.RedisError as e:
            print(f"Failed to retrieve tasks: {e}")
            return {}

if __name__ == "__main__":
    redis_service = RedisService()
    
    # print current tasks
    print(redis_service.get_all_tasks())
