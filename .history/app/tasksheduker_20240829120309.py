import time
import redis
import schedule
import httpx
import json
import os
from fastapi import HTTPException
from datetime import datetime, timedelta
from app.redis_service import RedisService
from typing import Dict, Any, Optional, Union, Literal
import pytz

class TaskScheduler(RedisService):
    def __init__(self, file_path: str = "tasks.json") -> None:
        super().__init__()
        self.tasks = {}
        self.file_path = file_path
        self.load_tasks()  

    def send_request(self, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]]) -> None:
        print(f"Sending {method.upper()} request to {url} with data: {data} and headers: {headers}")
        with httpx.Client() as client:
            try:
                if method == "get":
                    response = client.get(url, headers=headers, params=data)
                elif method == "post":
                    response = client.post(url, json=data, headers=headers)
                elif method == "put":
                    response = client.put(url, json=data, headers=headers)
                elif method == "delete":
                    response = client.delete(url, headers=headers, params=data)
                elif method == "patch":
                    response = client.patch(url, json=data, headers=headers)
                
                if response.status_code == 500 and self.conf().get('error_notification', {}).get('active', False):
                    self.send_error_email("Error when sending", f"There was an error while sending the request: {response.text}")
            except httpx.RequestError as e:
                self.send_error_email("Request Error", str(e))

    def schedule_one_time_task(self, task_id: int, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]], execute_at: str, timezone: str) -> None:
        print(f"Scheduling one-time task {task_id}")
        try:
            tz = pytz.timezone(timezone)
        except:
            tz = pytz.timezone("Europe/Amsterdam")
        execute_at_aware = tz.localize(datetime.strptime(execute_at, '%H:%M'))

        self.tasks[task_id] = {
            "type": "one_time",
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "execute_at": execute_at_aware.isoformat(),
            "timezone": timezone
        }
        self.save_tasks()

        now_aware = datetime.now(tz)
        if execute_at_aware < now_aware:
            execute_at_aware += timedelta(days=1)  # Schedule for the next day if time has passed

        # Schedule the task to run at the exact time
        run_time = execute_at_aware.strftime('%H:%M')
        print(f"Task {task_id} will run at {run_time}")
        schedule.every().day.at(run_time).do(self.run_scheduled_task, task_id)

    def schedule_interval_task(self, task_id: str, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]], timezone: str, execute_at: str, executions: Union[int, str] = 1) -> None:
        print(f"Scheduling interval task {task_id}")

        tz = pytz.timezone(timezone)
        execute_at_aware = tz.localize(datetime.strptime(execute_at, '%H:%M'))
        run_time = execute_at_aware.strftime('%H:%M')

        if isinstance(executions, int) and executions > 0:
            self.tasks[task_id] = {
                "type": "interval_with_number_of_times",
                "url": url,
                "method": method,
                "data": data,
                "headers": headers,
                "execute_at": execute_at_aware.isoformat(),
                "executions": executions,
                "timezone": timezone
            }
            self.save_tasks()
            print(f"Task {task_id} will run at {run_time} every day for {executions} times")

            def limited_execution_wrapper(task_id: str):
                if task_id in self.tasks:
                    self.run_scheduled_task(task_id)
            
            # Schedule the task with its ID as a tag
            schedule.every().day.at(run_time).do(limited_execution_wrapper, task_id).tag(task_id)

        elif executions == "*":
            self.tasks[task_id] = {
                "type": "interval_tasks_unlimited",
                "url": url,
                "method": method,
                "data": data,
                "headers": headers,
                "execute_at": execute_at_aware.isoformat(),
                "executions": executions,
                "timezone": timezone
            }
            self.save_tasks()
            print(f"Task {task_id} will run at {run_time} every day until the task is deleted")
            schedule.every().day.at(run_time).do(self.run_scheduled_task, task_id).tag(task_id)


        
    def schedule_limited_interval_task(self, task_id: int, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]], interval_minutes: int) -> None:
        self.tasks[task_id] = {
            "type": "interval_minutes_task",
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "interval_seconds": interval_minutes,
        }
        self.save_tasks()

        print(f"Executing a task every {interval_minutes} minutes as an id {task_id}")
        schedule.every(interval_minutes).minutes.do(self.run_scheduled_task, task_id).tag(task_id)

    def schedule_datetime_task(self, task_id: int, url: str, method: Literal["get", "post", "put", "delete", "patch"], data: Dict[str, Any], headers: Optional[Dict[str, Any]], timezone: str, datetime_task: datetime):
        tz = pytz.timezone(timezone)

        # Check if the datetime_task is naive or aware
        if datetime_task.tzinfo is None:
            # If naive, localize it
            execute_at_aware = tz.localize(datetime_task)
        else:
            # If already timezone-aware, convert to the desired timezone
            execute_at_aware = datetime_task.astimezone(tz)

        run_time = execute_at_aware.strftime('%H:%M')  # Corrected format to only time

        self.tasks[task_id] = {
            "type": "datetime_task",
            "url": url,
            "data": data,
            "method": method,
            "headers": headers,
            "timezone": timezone,
            "datetime_task": execute_at_aware.isoformat()
        }
        print(f"Scheduling a task that will be executed at {run_time} and has an id {task_id}")

        schedule.every().day.at(run_time).do(self.run_scheduled_task, task_id).tag(task_id)



    def run_scheduled_task(self, task_id: str) -> None:
        print(f"Attempting to run task {task_id}")
        task = self.tasks.get(task_id)
        
        if task:
            self.send_request(task["url"], task["method"], task["data"], task["headers"])
            if task["type"] == "one_time" or (task["type"] == "interval_with_number_of_times" and task["executions"] <= 1):
                del self.tasks[task_id]
            elif "executions" in task:
                task["executions"] -= 1
                if task["executions"] <= 0:
                    del self.tasks[task_id]
            self.save_tasks()
        else:
            print(f"Task {task_id} does not exist and will not be executed.")
            
    def save_tasks(self) -> None:
        """
        Save all tasks in the current dictionary to Redis.
        Each task is stored as a separate hash entry in the "tasks" key.
        """
        for task_id, task_data in self.tasks.items():
            self.save_task(task_id, task_data)
        print("All tasks have been saved to Redis.")


    def load_tasks(self) -> None:
        """
        Load the tasks from Redis into the tasks dictionary and schedule them.
        """
        self.tasks = self.get_all_tasks()
        if self.tasks:
            print("Tasks have been loaded from Redis.")
            self.schedule_loaded_tasks()
        else:
            print("No tasks found in Redis.")


    def schedule_loaded_tasks(self) -> None:
        """
        Reschedule the tasks after loading them from Redis.
        """
        for task_id, task in self.tasks.items():
            if task["type"] == "one_time":
                execute_at = datetime.fromisoformat(task["execute_at"])
                timezone = pytz.timezone(task["timezone"])
                now_aware = timezone.localize(datetime.utcnow())
                if now_aware < execute_at:
                    self.schedule_one_time_task(
                        task_id,
                        task["url"],
                        task["method"],
                        task["data"],
                        task["headers"],
                        execute_at.strftime('%H:%M'),
                        task["timezone"]
                    )
            elif task["type"] == "interval_with_number_of_times":
                execute_at = datetime.fromisoformat(task["execute_at"])
                timezone = pytz.timezone(task["timezone"])
                now_aware = timezone.localize(datetime.utcnow())
                executions = task["executions"]

                if now_aware < execute_at and executions > 0:
                    self.schedule_interval_task(
                        task_id,
                        task["url"],
                        task["method"],
                        task["data"],
                        task["headers"],
                        task["timezone"],
                        task["execute_at"],
                        executions=executions
                    )
            elif task["type"] == "interval_tasks_unlimited":
                execute_at = datetime.fromisoformat(task["execute_at"])
                timezone = pytz.timezone(task["timezone"])
                now_aware = timezone.localize(datetime.utcnow())

                if now_aware < execute_at:
                    self.schedule_interval_task(
                        task_id,
                        task["url"],
                        task["method"],
                        task["data"],
                        task["headers"],
                        task["timezone"],
                        task["execute_at"],
                        executions="*"
                    )
            elif task["type"] == "interval_minutes_task":
                interval = task["interval_seconds"]
                self.schedule_limited_interval_task(
                    task_id,
                    task["url"],
                    task["method"],
                    task["data"],
                    task["headers"],
                    interval
                )
            elif task["type"] == "datetime_task":
                datetime_task =  datetime.fromisoformat(task["datetime_task"])
                self.schedule_datetime_task(
                    task_id,
                    task["url"],
                    task["method"],
                    task["data"],
                    task["headers"],
                    
                )




    def delete_task(self, task_id: str) -> None:
        """Deletes a task by task_id and removes it from the schedule."""
        if task_id in self.tasks:
            print(f"Deleting task {task_id}")
            del self.tasks[task_id]
            super().delete_task(task_id)  # Call the delete_task method from RedisService
            # Clear the scheduled job from `schedule`
            schedule.clear(task_id)
        else:
            raise HTTPException(status_code=404, detail=f"Task {task_id} does not exist in the schedule node")



    def delete_all_tasks(self) -> None:
        """Delete all the tasks from both the in-memory dictionary and Redis."""
        self.tasks.clear()  # Clear the in-memory tasks dictionary
        super().delete_all()  # Call the delete_all method from RedisService to clear Redis
        schedule.clear()  # Clear all scheduled jobs
        print("All tasks have been deleted.")


    def conf(self) -> dict:
        if os.path.exists('config/conf_file.json'):
            with open('config/conf_file.json', 'r') as f:
                file_content = f.read()  
                return json.loads(file_content)  
        return {}

    def save_conf(self, configuration: dict):
        if os.path.exists('config/conf_file.json'):
            with open('config/conf_file.json', 'w') as f:
                json.dump(configuration, f)
        else:
            raise FileNotFoundError("conf_file.json doesn't exist")

    def send_error_email(self, error_name, error_description):
        url = "http://18.116.69.127:8000/notificate_node_issue"
        data = {
            "error_type": "bug",
            "description": f"Error name: {error_name} | Description: {error_description}"
        }
        with httpx.Client() as client:
            client.post(url=url, json=data)

def get_timezone(client_ip) -> str:
    with httpx.Client() as client:
        response = client.get(f"https://ipinfo.io/{client_ip}/json")
        response_data = response.json()
        timezone = response_data.get('timezone', 'Europe/Amsterdam')
        return timezone


def proofs():
    scheduler = TaskScheduler()

    task_data = {
        "url": "http://3.141.197.183:8000/notificate_node_issue",
        "method": "post",
        "data": { "error_type": "bug", "description": "idk if it works but if u are rividing this i love u"},
        "headers": {},
        "execute_at": "12:47",
        "timezone": "Europe/Amsterdam"
    }

    scheduler.schedule_one_time_task(
        task_id=1,
        url=task_data["url"],
        method=task_data["method"],
        data=task_data["data"],
        headers=task_data["headers"],
        execute_at=task_data["execute_at"],
        timezone=task_data["timezone"]
    )

if __name__ == "__main__":
    scheduler = TaskScheduler()
    proofs()

    while True:
        schedule.run_pending()
        time.sleep(1)
