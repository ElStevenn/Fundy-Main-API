from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app import redis_service, schemas, tasksheduker
from app.founding_rate_service.main_sercice_layer import FoundinRateService
import uuid, asyncio, schedule, os


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(run_scheduler())
    yield

app = FastAPI(
    title="Schedule Task Node",
    description=(
        "This API allows users to schedule and manage recurring or one-time HTTP tasks based on specific time intervals or a specified future time. "
        "You can schedule tasks to run at regular intervals, delete tasks, and retrieve the status of scheduled tasks. "
        "It's designed for automation and can handle tasks such as periodic data fetching, notifications, and more.\n\n"
        
        "### Authentication:\n"
        "This API requires authentication to access most endpoints. Please include your API key in the `Authorization` header "
        "as a Bearer token when making requests. For example:\n"
        "```\n"
        "Authorization: Bearer YOUR_API_KEY\n"
        "```\n"
        
        "### Key Features:\n"
        "- **Schedule Recurring Tasks**: Schedule tasks to run at fixed intervals (e.g., every X minutes).\n"
        "- **Schedule One-Time Tasks**: Schedule an HTTP request to be executed at a specific time in the future.\n"
        "- **Automatic Timezone Detection**: If a timezone isn't provided, the server will detect the client's timezone based on their IP address.\n"
        "- **Unique Task Identification**: Each scheduled task is assigned a unique UUID for tracking and management.\n"
        "- **Task Management**: Retrieve the list of all scheduled tasks, and delete individual tasks or all tasks at once.\n\n"
        
        "### Summary:\n"
        "The Schedule Task Node API is a flexible tool for automating both recurring and one-time HTTP requests, making it ideal for "
        "applications that require regular data polling, notifications, or any scheduled tasks that need precise timing."
    ),
    lifespan=lifespan,
    version="1.0",
    servers=[{"url":"http://3.143.209.3/", "description":"USA"},{"url":"http://localhost/", "description":"EU"}]
)


origins = [
    "http://",
    "http://0.0.0.0:80",
    "http://localhost",
    "http://3.143.209.3/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


task_scheduler = tasksheduker.TaskScheduler()
redis_service_ = redis_service.RedisService()
founding_rate_service = FoundinRateService()
background_task = None 


app.mount("/mini_frontend", StaticFiles(directory="frontend"), name="static")

@app.get("/", include_in_schema=False)
async def root():
    content = open("frontend/index.html")
    return HTMLResponse(content.read())

async def run_scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)



# PART 1 | TIME SCHEDULE TASKS
@app.post(
    "/schedule_one_time", 
    description=(
        "**Schedule a One-Time Task**\n\n"
        "This endpoint allows you to schedule an HTTP request to be executed at a specific time in the future. "
        "You can specify details such as the URL, HTTP method, headers, and data payload, and the request will be automatically triggered at the specified time.\n\n"
        "### Key Features:\n"
        "- **Automatic Timezone Detection**: If you don't provide a timezone, the server will automatically detect the client's timezone based on their IP address.\n"
        "- **Unique Task Identification**: Each scheduled task is assigned a unique UUID, which can be used to track or cancel the task later.\n"
        "- **Flexible Scheduling**: You can schedule tasks using any valid HTTP method (e.g., GET, POST, PUT, DELETE) and include headers and data as needed.\n\n"
        "### Request Parameters:\n"
        "- **url**: The endpoint where the HTTP request will be sent.\n"
        "- **method**: The HTTP method to use (`GET`,`POST`,`PUT`,`DELETE`,`PATCH`).\n"
        "- **data**: The JSON payload to include in the request body (optional).\n"
        "- **headers**: Any custom headers to include in the request (optional).\n"
        "- **execute_at**: The specific time when the request should be sent (format: `HH:MM`).\n"
        "- **timezone**: (Optional) The timezone to use for scheduling the task. If not provided, the server will determine the client's timezone automatically.\n\n"
        "### Response:\n"
        "On success, the endpoint returns:\n"
        "- **status**: `success`\n"
        "- **task_id**: A unique UUID for the scheduled task.\n"
        "- **message**: A confirmation message.\n"
        "- **timezone**: The timezone used to schedule the task.\n\n"
        "If an error occurs, the response will include an `error` message with details about the issue."
    ), 
    tags=["Schedule By Time"]
)
async def schedule_new_task(
    request: Request, 
    request_body: schemas.OneTimeTask, 
    background_tasks: BackgroundTasks
):
    try:
        if not request_body.timezone:
            client_ip = request.client.host
            client_timezone = tasksheduker.get_timezone(client_ip)
        else:
            client_timezone = request_body.timezone

        task_id = str(uuid.uuid4())
        task_scheduler.schedule_one_time_task(
            task_id=task_id, 
            url=request_body.url, 
            method=request_body.method, 
            data=request_body.data, 
            headers=request_body.headers,
            execute_at=request_body.execute_at,
            timezone=client_timezone
        )

        # background_tasks.add_task(run_scheduler) 
        
        return {"status": "success", "task_id": task_id, "message": "The task for one time has been successfully scheduled", "timezone": client_timezone}
    except Exception as e:
        return {"status": "error", "message": f"There was an unexpected error scheduling a task: {e}"}


@app.post(
    "/schedule_interval", 
    description=(
        "**Schedule a Recurring Task**\n\n"
        "This endpoint allows you to schedule a recurring HTTP request that will be executed every day at a specified time. "
        "You can configure the task to run a specific number of times or to run indefinitely until it is manually deleted.\n\n"
        
        "### How It Works:\n"
        "When you call this endpoint, you provide the details of the HTTP request, including the URL, HTTP method, any necessary data or headers, "
        "and the time at which the request should be sent each day. Optionally, you can specify how many times the task should run.\n\n"
        
        "### Request Parameters:\n"
        "- **url**: The endpoint where the HTTP request will be sent. This should be a valid URL.\n"
        "- **method**: The HTTP method to use for the request. Supported methods include `GET`, `POST`, `PUT`, `DELETE`, and `PATCH`.\n"
        "- **data**: (Optional) A JSON object containing the data to be sent with the request. This is typically used with `POST` and `PUT` methods.\n"
        "- **headers**: (Optional) A JSON object containing any HTTP headers that should be included in the request.\n"
        "- **execute_at**: The specific time each day when the request should be sent. The time should be in the format `HH:MM` (24-hour clock).\n"
        "- **timezone**: (Optional) The timezone to use when scheduling the task. If not provided, the server will automatically detect the client's timezone based on their IP address.\n"
        "- **executions**: The number of times the task should run. If set to `*` or `-1`, the task will run indefinitely until manually deleted.\n\n"
        
        "### Response:\n"
        "The response will indicate whether the task was successfully scheduled, along with a unique `task_id` that you can use to reference the task in future operations.\n"
        "If the task is set to run a specific number of times, the response will include that information. If the task is set to run indefinitely, the response will indicate that as well.\n\n"
        
        "### Example Usage:\n"
        "1. **Schedule a Task to Run 5 Times**\n\n"
        "   Request Body:\n"
        "   ```json\n"
        "   {\n"
        "       \"url\": \"https://api.example.com/data\",\n"
        "       \"method\": \"POST\",\n"
        "       \"data\": {\"key\": \"value\"},\n"
        "       \"headers\": {\"Authorization\": \"Bearer token\"},\n"
        "       \"execute_at\": \"14:30\",\n"
        "       \"timezone\": \"Europe/Amsterdam\",\n"
        "       \"executions\": 5\n"
        "   }\n"
        "   ```\n\n"
        "   Response:\n"
        "   ```json\n"
        "   {\n"
        "       \"status\": \"success\",\n"
        "       \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\",\n"
        "       \"message\": \"The task has been scheduled to run 5 times.\"\n"
        "   }\n"
        "   ```\n\n"
        
        "2. **Schedule a Task to Run Indefinitely**\n\n"
        "   Request Body:\n"
        "   ```json\n"
        "   {\n"
        "       \"url\": \"https://api.example.com/data\",\n"
        "       \"method\": \"GET\",\n"
        "       \"execute_at\": \"09:00\",\n"
        "       \"timezone\": \"America/New_York\",\n"
        "       \"executions\": \"*\"\n"
        "   }\n"
        "   ```\n\n"
        "   Response:\n"
        "   ```json\n"
        "   {\n"
        "       \"status\": \"success\",\n"
        "       \"task_id\": \"123e4567-e89b-12d3-a456-426614174001\",\n"
        "       \"message\": \"The task will run indefinitely until manually deleted.\"\n"
        "   }\n"
        "   ```\n\n"
        
        "### Error Handling:\n"
        "If there is an error while scheduling the task, the response will contain an error message detailing what went wrong. This could happen due to invalid parameters, an issue with the request format, or other unexpected errors.\n\n"
        
        "### Notes:\n"
        "- You can use the `task_id` returned in the response to delete or query the status of the scheduled task.\n"
        "- The task will continue to run every day at the specified time until the specified number of executions is reached or until it is manually deleted."
    ), 
    tags=["Schedule By Time"],
    response_model=schemas.Return_SON
)
async def schedule_interval(request: Request, request_body: schemas.LimitedIntervalTask, background_tasks: BackgroundTasks):
    try:
        if not request_body.timezone:
            client_ip = request.client.host
            client_timezone = tasksheduker.get_timezone(client_ip)
        else:
            client_timezone = request_body.timezone
        
        task_id = str(uuid.uuid4())
        task_scheduler.schedule_interval_task(
            task_id=task_id,
            url=request_body.url, 
            method=request_body.method,
            data=request_body.data,
            headers=request_body.headers,
            timezone=client_timezone,
            execute_at=request_body.execute_at,
            executions=request_body.executions
        )

        if request_body.executions == "*" or request_body.executions == -1:
            message = "The task will run indefinitely until manually deleted."
        else:
            message = f"The task has been scheduled to run {request_body.executions} times."

        return {"status": "success", "task_id": task_id, "message": message, "task_id": task_id, "timezone": client_timezone}
    except Exception as e:
        return {"status": "error", "message": f"There was an unexpected error scheduling a task: {e}"}

@app.post(
    "/schedule_interval_minutes", 
    description=(
        "**Schedule a Recurring Task by Minutes**\n\n"
        "This endpoint allows you to schedule a recurring HTTP request that will be executed every X minutes indefinitely. "
        "Once scheduled, the task will continue to run at the specified interval until it is manually deleted or the server is stopped.\n\n"
        
        "### How It Works:\n"
        "When you call this endpoint, you provide the details of the HTTP request, including the URL, HTTP method, any necessary data or headers, "
        "and the interval in minutes at which the request should be sent. The task will automatically be assigned a unique ID that you can use to manage it later.\n\n"
        
        "### Request Parameters:\n"
        "- **url**: The endpoint where the HTTP request will be sent. This should be a valid URL.\n"
        "- **method**: The HTTP method to use for the request. Supported methods include `GET`, `POST`, `PUT`, `DELETE`, and `PATCH`.\n"
        "- **data**: (Optional) A JSON object containing the data to be sent with the request. This is typically used with `POST` and `PUT` methods.\n"
        "- **headers**: (Optional) A JSON object containing any HTTP headers that should be included in the request.\n"
        "- **interval_minutes**: The interval in minutes at which the task should be executed.\n\n"
        
        "### Response:\n"
        "The response will indicate whether the task was successfully scheduled, along with a unique `task_id` that you can use to reference the task in future operations.\n"
        "The response will also include a message confirming that the task has been scheduled to run every specified number of minutes indefinitely.\n\n"
        
        "### Example Usage:\n"
        "1. **Schedule a Task to Run Every 15 Minutes**\n\n"
        "   Request Body:\n"
        "   ```json\n"
        "   {\n"
        "       \"url\": \"https://api.example.com/notify\",\n"
        "       \"method\": \"POST\",\n"
        "       \"data\": {\"message\": \"Hello, World!\"},\n"
        "       \"headers\": {\"Authorization\": \"Bearer token\"},\n"
        "       \"interval_minutes\": 15\n"
        "   }\n"
        "   ```\n\n"
        "   Response:\n"
        "   ```json\n"
        "   {\n"
        "       \"status\": \"success\",\n"
        "       \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\",\n"
        "       \"message\": \"The task has been scheduled and will be executed every 15 minutes.\"\n"
        "   }\n"
        "   ```\n\n"
        
        "### Error Handling:\n"
        "If there is an error while scheduling the task, the response will contain an error message detailing what went wrong. This could happen due to invalid parameters, "
        "an issue with the request format, or other unexpected errors.\n\n"
        
        "### Notes:\n"
        "- You can use the `task_id` returned in the response to delete or query the status of the scheduled task.\n"
        "- The task will continue to run every specified number of minutes until it is manually deleted."
    ), 
    tags=["Schedule By Time"]
)
async def schedule_limited_minutes(request_body: schemas.IntervalMinutesTask, background_tasks: BackgroundTasks):
    try:

        task_id = str(uuid.uuid4())
        task_scheduler.schedule_limited_interval_task(
            task_id=task_id,
            url=request_body.url,
            method=request_body.method,
            data=request_body.data,
            headers=request_body.headers,
            interval_minutes=request_body.interval_minutes
        )

        return {"status": "success", "task_id": task_id, "message": f"The task has been scheduled and will be executed every {request_body.interval_minutes} minutes"}
    except Exception as e:
        return {"status": "error", "message": f"There was an unexpected error executing a limited number of tasks: {e}"}


@app.post(
    "/schedule_datetime", 
    description=(
        "**Schedule a Task for a Specific Datetime**\n\n"
        "This endpoint allows you to schedule an HTTP request to be executed at a specific date and time in the future. "
        "You can specify details such as the URL, HTTP method, headers, and data payload, and the request will be automatically triggered at the specified datetime.\n\n"
        
        "### Key Features:\n"
        "- **Timezone Handling**: The request will be executed according to the specified timezone. If the datetime provided is naive (without timezone info), it will be localized to the specified timezone.\n"
        "- **Unique Task Identification**: Each scheduled task is assigned a unique UUID, which can be used to track or cancel the task later.\n"
        "- **Flexible Scheduling**: You can schedule tasks using any valid HTTP method (e.g., GET, POST, PUT, DELETE) and include headers and data as needed.\n\n"
        
        "### Request Parameters:\n"
        "- **url**: The endpoint where the HTTP request will be sent. This should be a valid URL.\n"
        "- **method**: The HTTP method to use for the request. Supported methods include `GET`, `POST`, `PUT`, `DELETE`, and `PATCH`.\n"
        "- **data**: (Optional) A JSON object containing the data to be sent with the request. This is typically used with `POST` and `PUT` methods.\n"
        "- **headers**: (Optional) A JSON object containing any HTTP headers that should be included in the request.\n"
        "- **datetime_task**: The specific datetime when the request should be sent. This should be provided in ISO 8601 format.\n"
        "- **timezone**: (Optional) The timezone to use when scheduling the task. If not provided, the server will use the timezone information from `datetime_task` or assume UTC.\n\n"
        
        "### Response:\n"
        "The response will indicate whether the task was successfully scheduled, along with a unique `task_id` that you can use to reference the task in future operations.\n\n"
        
        "### Example Usage:\n"
        "1. **Schedule a Task to Run at a Specific Datetime**\n\n"
        "   Request Body:\n"
        "   ```json\n"
        "   {\n"
        "       \"url\": \"https://api.example.com/notify\",\n"
        "       \"method\": \"POST\",\n"
        "       \"data\": {\"message\": \"Hello, World!\"},\n"
        "       \"headers\": {\"Authorization\": \"Bearer token\"},\n"
        "       \"datetime_task\": \"2024-08-16T14:30:00\",\n"
        "       \"timezone\": \"Europe/Amsterdam\"\n"
        "   }\n"
        "   ```\n\n"
        "   Response:\n"
        "   ```json\n"
        "   {\n"
        "       \"status\": \"success\",\n"
        "       \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\",\n"
        "       \"message\": \"The task has been scheduled to run at the specified datetime.\"\n"
        "   }\n"
        "   ```\n\n"
        
        "### Error Handling:\n"
        "If there is an error while scheduling the task, the response will contain an error message detailing what went wrong. This could happen due to invalid parameters, "
        "an issue with the request format, or other unexpected errors.\n\n"
        
        "### Notes:\n"
        "- You can use the `task_id` returned in the response to delete or query the status of the scheduled task."
    ),
    tags=["Schedule By Time"]
)
async def schedule_a_task_datetime(request_boddy: schemas.DatetimeTask, background_tasks: BackgroundTasks):
    try:
        task_id = str(uuid.uuid4())
        task_scheduler.schedule_datetime_task(
            task_id=task_id,
            url=request_boddy.url,
            method=request_boddy.method,
            data=request_boddy.data,
            headers=request_boddy.headers,
            timezone=request_boddy.timezone,
            datetime_task=request_boddy.task_datetime # date and time when the task must be executed and ISO format
        )
        

        return {"status": "success", "message": "Datetime task has been successfully scheduled at {request_boddy.task_datetime}", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"There was an unexpected error while scheduling datetime task: {e}")

@app.get(
    "/tasks", 
    description=(
        "Retrieve all scheduled tasks.\n\n"
        "This endpoint returns a list of all tasks currently scheduled. "
        "Each task is identified by a unique `task_id` and includes key details like the URL, HTTP method, and scheduling interval.\n\n"
        
        "### Example Response:\n"
        "```json\n"
        "{\n"
        "   \"123e4567-e89b-12d3-a456-426614174000\": {\n"
        "       \"url\": \"https://api.example.com/notify\",\n"
        "       \"method\": \"POST\",\n"
        "       \"interval_minutes\": 15\n"
        "   }\n"
        "}\n"
        "```\n"
    ), 
    tags=["Schedule By Time"]
)
async def list_tasks():
    tasks = redis_service_.get_all_tasks()
    return tasks

@app.delete(
    "/delete_task/{task_id}", 
    description=(
        "Delete a scheduled task by its ID.\n\n"
        "This endpoint allows you to delete a specific task using its unique `task_id`. "
        "Once deleted, the task will no longer be executed.\n\n"
        
        "### Example Usage:\n"
        "```\n"
        "DELETE /delete_task/123e4567-e89b-12d3-a456-426614174000\n"
        "```\n"
        
        "### Example Response:\n"
        "```json\n"
        "{\n"
        "   \"status\": \"success\",\n"
        "   \"message\": \"Task with ID 123e4567-e89b-12d3-a456-426614174000 has been deleted!\"\n"
        "}\n"
        "```\n"
        
        "### Error Handling:\n"
        "If the task cannot be found or an error occurs during deletion, an error message will be returned."
    ), 
    tags=["Schedule By Time"]
)
async def remove_task(task_id: str):
    task_scheduler.delete_task(task_id)
    return {"status": "success", "message": f"Task with ID {task_id} has been deleted!"}

@app.delete(
    "/delete_all_tasks", 
    description=(
        "Delete all scheduled tasks.\n\n"
        "This endpoint removes all tasks that have been scheduled. "
        "After calling this, no tasks will remain in the scheduler.\n\n"
        
        "### Example Usage:\n"
        "```\n"
        "DELETE /delete_all_tasks\n"
        "```\n"
        
        "### Example Response:\n"
        "```json\n"
        "{\n"
        "   \"status\": \"success\",\n"
        "   \"message\": \"All tasks have been deleted successfully.\"\n"
        "}\n"
        "```\n"
    ), 
    tags=["Schedule By Time"]
)
async def remove_all_tasks():
    task_scheduler.delete_all_tasks()
    return {"status": "success", "message": "all the tasks has been delted successfully"}

# PART CONFIGURATION |
@app.get("/conf", include_in_schema=False)
async def get_schedule_node_configuration():
    return task_scheduler.conf()

@app.post("/save-config", include_in_schema=False)
async def set_new_configuration(request: Request):

    # Get config and then save it 
    config = await request.json()
    print(config)
    task_scheduler.save_conf(config)
    return {"message": "Configuration saved successfully"}



# PART 2 | CRYPTO / INDEX reach a certain price
@app.put(
    "/add_new_alert", 
    description=(
        "Add a new alert for when a cryptocurrency reaches a specific price.\n\n"
        "This endpoint is intended to allow users to set up alerts for when a specified cryptocurrency reaches a target price. "
        "However, this feature is currently under development and is not available at this time.\n\n"
        
        "### Current Status:\n"
        "This feature is under development and will be available in a future release."
    ), 
    tags=["Schedule By Crypto"]
)
async def add_new_alert_if_crypto_reaches_price(request_body: schemas.CryptoAlertTask):
    # Placeholder for future implementation
    return {"status": "success", "message": "This feature is under development"}




# PART 3 | FOUNDING RATE SERVICE

@app.get("/founding_rate_service/status", description="", tags=['Founding Rate Service'])
async def see_founding_rate_service():
    """Check the status of the Founding Rate Service."""
    global background_task
    if background_task and not background_task.done():
        return {"status": "running"}
    else:
        return {"status": "stopped"}


@app.post("/founding_rate_service/start", description="", tags=['Founding Rate Service'])
async def start_founding_rate_service(background_tasks: BackgroundTasks):
    """Start the Founding Rate Service."""
    global background_task
    if background_task and not background_task.done():
        raise HTTPException(status_code=400, detail="Service is already running")

    # Start the service using the correct method
    background_task = background_tasks.add_task(founding_rate_service.start_service)  # Correct method to handle scheduling
    return {"status": "Service started"}


@app.delete("/founding_rate_service/stop", description="", tags=['Founding Rate Service'])
async def stop_founding_rate_service():
    """Stop the Founding Rate Service."""
    global background_task
    if background_task and not background_task.done():
        background_task.cancel()  # Correctly stop the task
        return {"status": "Service stopped"}
    else:
        raise HTTPException(status_code=400, detail="Service is not running")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=80)
