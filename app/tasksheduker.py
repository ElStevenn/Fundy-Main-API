import time
import threading
import requests
from typing import Dict, Any, Optional, Union, Literal
import json
import os
from datetime import datetime
import pytz

TIMEZONE = 'Europe/Amsterdam'

class TaskScheduler:
    def __init__(self, file_path: str = "tasks.json") -> None:
        self.tasks = {}
        self.file_path = file_path
        self.load_tasks()

    def send_request(self, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]]) -> None:
        if method == "get":
            response = requests.get(url, headers=headers, params=data)
        elif method == "post":
            response = requests.post(url, json=data, headers=headers)
        elif method == "put":
            response = requests.put(url, json=data, headers=headers)
        elif method == "delete":
            response = requests.delete(url, headers=headers, params=data)
        elif method == "patch":
            response = requests.patch(url, json=data, headers=headers)
        if response.status_code == 500 and self.conf['error_notification']['active']:
            self.send_error_email("Error when sending", f"There was an error while sending the request: {response.text}")

    def schedule_one_time_task(self, task_id: int, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]], execute_at: str) -> None:
        amsterdam_tz = pytz.timezone(TIMEZONE)
        execute_at_aware = amsterdam_tz.localize(datetime.strptime(execute_at, '%H:%M'))

        self.tasks[task_id] = {
            "type": "one_time",
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "execute_at": execute_at_aware.strftime('%H:%M')
        }
        self.save_tasks()

    def schedule_interval_task(self, task_id: int, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]], interval_seconds: int) -> None:
        self.tasks[task_id] = {
            "type": "interval",
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "interval_seconds": interval_seconds,
            "next_run": time.time() + interval_seconds
        }
        self.save_tasks()

    def schedule_limited_interval_task(self, task_id: int, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]], interval_seconds: int, executions: Union[int, str]) -> None:
        self.tasks[task_id] = {
            "type": "limited_interval",
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "interval_seconds": interval_seconds,
            "executions": executions,
            "next_run": time.time() + interval_seconds
        }
        self.save_tasks()

    def save_tasks(self) -> None:
        serializable_tasks = {task_id: task for task_id, task in self.tasks.items()}
        with open(self.file_path, "w") as file:
            json.dump(serializable_tasks, file)

    def get_tasks(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                tasks = json.load(file)
        return tasks

    def load_tasks(self) -> None:
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                try:
                    tasks = json.load(file)
                except json.JSONDecodeError:
                    tasks = {}
                self.tasks = tasks

    def run_scheduler(self) -> None:
        amsterdam_tz = pytz.timezone(TIMEZONE)
        while True:
            now = datetime.now(amsterdam_tz).strftime('%H:%M')
            for task_id, task in list(self.tasks.items()):
                if task["type"] == "one_time" and task["execute_at"] == now:
                    self.send_request(task["url"], task["method"], task["data"], task["headers"])
                    del self.tasks[task_id]
                elif task["type"] == "interval" and time.time() >= task["next_run"]:
                    self.send_request(task["url"], task["method"], task["data"], task["headers"])
                    task["next_run"] = time.time() + task["interval_seconds"]
                elif task["type"] == "limited_interval" and time.time() >= task["next_run"]:
                    if task["executions"] == "*" or task["executions"] > 0:
                        self.send_request(task["url"], task["method"], task["data"], task["headers"])
                        task["next_run"] = time.time() + task["interval_seconds"]
                        if task["executions"] != "*":
                            task["executions"] -= 1
                    if task["executions"] == 0:
                        del self.tasks[task_id]
            self.save_tasks()
            time.sleep(1)

    def start(self) -> None:
        scheduler_thread = threading.Thread(target=self.run_scheduler)
        scheduler_thread.start()

    def delete_task(self, task_id: int) -> None:
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.save_tasks()

    @property
    def conf(self):
        return json.loads(open('conf_file.json').read())

    def set_conf(self, key, value):
        _conf = self.conf
        _conf[key] = value
        self.save_conf(_conf)

    def save_conf(self, new_conf):
        with open('conf_file.json', 'w') as f:
            f.write(json.dumps(new_conf, indent=4))

    def save_whole_conf(self, data):
        with open('conf_file.json', 'w') as f:
            f.write(json.dumps(data, indent=4))

    def del_conf(self, key):
        _conf = self.conf
        del _conf[key]
        self.save_conf(_conf)

    def send_error_email(self, error_name, error_description):
        url = "http://18.116.69.127:8000/notificate_node_issue"
        data = {
            "error_type": "bug",
            "description": f"Error name: {error_name} | Description: {error_description}"
        }
        requests.post(url=url, data=data)



if __name__ == "__main__":
    task_scheduler = TaskScheduler()
    task_scheduler.start()
    # test_schedule_one_time_task()
