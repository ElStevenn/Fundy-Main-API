from fastapi import FastAPI, requests
from app import schemas, orm, tasksheduker, asset_alerts
import uuid

app = FastAPI(title="Schedule Task Node", description="")
task_scheduler = tasksheduker.TaskScheduler()

# PART 1 | TIME SCHEDULE TASKS
@app.post("/schedule_one_time", description="Schedule a task that will be executed only one single time", tags=["Schedule By Time"])
async def shedule_new_task(reqest_boddy: schemas.OneTimeTask):
    try:
        task_id = str(uuid.uuid4())
        task_scheduler.schedule_one_time_task(
            task_id=task_id, 
            url=reqest_boddy.url, 
            method=reqest_boddy.method, 
            data=reqest_boddy.data, 
            headers=reqest_boddy.headers,
            execute_at=reqest_boddy.execute_at
            )
        return {"status": "success", "task_id": task_id, "message": "The task for one time, has been sucess executed"}
    except Exception as e:
        return {"status": "error", "message": f"There was an unexcepted error with schedule a single task {e}"}

@app.post("/schedule_interval", description="Schedule task specific number of times or always", tags=["Schedule By Time"])
async def schedule_interval(request_boddy: schemas.LimitedIntervalTask):
    try:
        task_id = str(uuid.uuid4())
        task_scheduler.schedule_interval_task(
            task_id=task_id,
            url=request_boddy.url, 
            method=request_boddy.method
        )
        return {"status": "success", "task_id": task_id, "message": "The interval task has been scheduled!"}
    except Exception as e:
        return {"status": "error", "message": f"There was an unexcepted error with schedule a task {e}"}

@app.post("/schedule_limited_interval", description="Schedule a task for limited number of times", tags=["Schedule By Time"])
async def  schedule_limited_interval(request_boddy: schemas.LimitedIntervalTask):
    try:
        task_id = str(uuid.uuid4())
        task_scheduler.schedule_limited_interval_task(
            task_id=task_id,
            url=request_boddy.url,
            method=request_boddy.method,
            data=request_boddy.data,
            headers=request_boddy.headers,
            interval_seconds=request_boddy.interval_seconds,
            executions=request_boddy.executions
        )
        return {"status": "success", "task_id": task_id, "message": "The task has been sheduled!"}
    except Exception as e:
        return {"status": "error", "message": f"There was an unexcepted error with executing a limited number of tasks:  {e}"}


@app.get("/tasks", description="Get all scheduled tasks", tags=["Schedule By Time"])
async def list_tasks():
    tasks = {task_id: {k: v for k, v in task.items() if k != "job"} for task_id, task in task_scheduler.tasks.items()}
    return tasks

@app.delete("/delete_task/{task_id}", description="delete a task by its id", tags=["Schedule By Time"])
async def remove_task(task_id: str):
    try:
        task_scheduler.delete_task(task_id)
        return {"status": "success", "message": f"Task with id {task_id} has been deleted!"}
    except Exception as e:
        return {"status": "error", "message": f"There was an unexecepted errror: {e}"}


# PART CONFIGURATION |
@app.get("/conf", description="Get configuration of this node in json format", tags=["Shedule node configuration"])
async def get_shedule_node_configuration():
    return task_scheduler.conf

@app.post("/conf", description="Set whole configuration", tags=["Shedule node configuration"])
async def set_new_configuration(request_boddy: schemas.WholeConfiguration):
    task_scheduler.save_whole_conf()
    return task_scheduler.conf

@app.put("/conf/{key}/{value}", description="set key configuration", tags=["Shedule node configuration"])
async def set_value_conf():
    task_scheduler.set_conf()
    return task_scheduler.conf

@app.delete("/conf/{key}", description="Delete key configuration", tags=["Shedule node configuration"])
async def delete_part_of_conf(key: str):
    task_scheduler.del_conf(key)
    return task_scheduler.conf


# PART 2 | CRYPTO / INDEX reach a certain price
@app.put("/add_new_alert", tags=["Schedule By Crypto"])
async def add_new_alert_if_crypto_reaches_price(request_boddy: schemas.CryptoAlertTask):
    return 


if __name__ == "__main__":
    import uvicorn
    task_scheduler.start()
    uvicorn.run(app, host='0.0.0.0', port=80, access_log=False)
    