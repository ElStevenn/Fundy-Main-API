import time
import socket
import redis
import schedule
import httpx
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, Literal
import pytz

class RedisService:
    def __init__(self):
        hostname = socket.gethostname()
            
        if hostname == 'expected_server_hostname':  
            redis_host = 'redis_tasks'  
        else:
            redis_host = 'localhost' 
        
        self._r = redis.Redis(host=redis_host, port=6379, decode_responses=True)
        self.ensure_correct_key_type()

    def ensure_correct_key_type(self):
        """Ensure the 'tasks' key is a hash or delete it if not."""
        if self._r.exists("tasks") and self._r.type("tasks") != "hash":
            print(f"Deleting the incorrect 'tasks' key of type {self._r.type('tasks')}.")
            self._r.delete("tasks")

    def save_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Save a task to Redis as a hash entry."""
        self.ensure_correct_key_type()
        self._r.hset("tasks", task_id, json.dumps(task_data))
        print(f"Task '{task_id}' saved successfully.")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task from Redis by its ID."""
        task_data = self._r.hget("tasks", task_id)
        if task_data:
            return json.loads(task_data)
        else:
            print(f"Task '{task_id}' not found.")
            return None

    def delete_task(self, task_id: str) -> None:
        """Delete a task from Redis."""
        result = self._r.hdel("tasks", task_id)
        if result:
            print(f"Task '{task_id}' deleted successfully.")
        else:
            print(f"Task '{task_id}' not found or could not be deleted.")

    def get_all_tasks(self) -> Dict[str, Any]:
        """Retrieve all tasks from Redis."""
        self.ensure_correct_key_type()
        tasks = self._r.hgetall("tasks")
        return {task_id: json.loads(task_data) for task_id, task_data in tasks.items()}

    def delete_all(self) -> None:
        """Delete all tasks in Redis."""
        self._r.delete("tasks")
        print("All tasks have been deleted from Redis.")

if __name__ == "__main__":
    redis_service = RedisService()

    # Define a task with a unique ID
    task_id = "task_1"
    task_data = {
        "url": "http://example.com/api/notify",
        "method": "post",
        "data": {"message": "Hello World"},
        "headers": {"Content-Type": "application/json"},
        "execute_at": "12:00",
        "timezone": "Europe/Amsterdam"
    }

    # Save the task to Redis
    redis_service.save_task(task_id, task_data)
    # print(redis_service.get_all_tasks())