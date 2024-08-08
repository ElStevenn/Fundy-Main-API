import time
import threading
import httpx
import asyncio
import requests
from typing import Dict, Any, Optional, Union, Literal
import json, os
from datetime import datetime, timedelta
import pytz
import schedule

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

    def schedule_one_time_task(self, task_id: int, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]], execute_at: str, timezone: str) -> None:
        tz = pytz.timezone(timezone)
        execute_at_aware = tz.localize(datetime.strptime(execute_at, '%H:%M'))

        self.tasks[task_id] = {
            "type": "one_time",
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "execute_at": execute_at_aware.strftime('%H:%M'),
            "timezone": timezone  # Save the timezone with the task
        }
        self.save_tasks()

        # Calculate the delay in seconds until the task should be executed
        now_aware = datetime.now(tz)
        delay_seconds = (execute_at_aware - now_aware).total_seconds()
        if delay_seconds < 0:
            delay_seconds += 86400  # Add a day's worth of seconds if time has already passed today

        threading.Timer(delay_seconds, self.run_scheduled_task, args=[task_id]).start()

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
        schedule.every(interval_seconds).seconds.do(self.run_scheduled_task, task_id=task_id)

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
        for _ in range(int(executions) if executions != "*" else 1):
            schedule.every(interval_seconds).seconds.do(self.run_scheduled_task, task_id=task_id)

    def run_scheduled_task(self, task_id: int) -> None:
        task = self.tasks.get(task_id)
        if task:
            self.send_request(task["url"], task["method"], task["data"], task["headers"])
            if task["type"] == "one_time":
                del self.tasks[task_id]
            elif task["type"] == "limited_interval" and task["executions"] != "*":
                task["executions"] -= 1
                if task["executions"] == 0:
                    del self.tasks[task_id]
            self.save_tasks()

    def save_tasks(self) -> None:
        serializable_tasks = {task_id: task for task_id, task in self.tasks.items()}
        with open(self.file_path, "w") as file:
            json.dump(serializable_tasks, file)

    def load_tasks(self) -> None:
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                try:
                    tasks = json.load(file)
                except json.JSONDecodeError:
                    tasks = {}
                self.tasks = tasks

    def run_scheduler(self) -> None:
        while True:
            schedule.run_pending()
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

async def get_timezone(client_ip) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://ipinfo.io/{client_ip}/json")
        response_data = response.json()
        timezone = response_data.get('timezone', 'Europe/Amsterdam')
        return timezone

async def proofs():
    timezone = await get_timezone("92.189.163.252")
    print("timezone -> ", timezone)

if __name__ == "__main__":
    asyncio.run(proofs())
