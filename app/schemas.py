from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List, Union, Literal
from datetime import datetime
import uuid

class BaseTask(BaseModel):
    url: str
    method: Literal["get", "post", "put", "delete", "patch"] = "post"
    data: Dict[str, Any]
    headers: Optional[Dict[str, Any]] = Field(default_factory=lambda: {'Content-Type': 'application/json'})
    timezone: Optional[str] = None

class OneTimeTask(BaseTask):
    execute_at: str  # If value is '18:00' it will be executed at '18:00' today or tomorrow. Otherwise, the value could be '2024-09-13-18:00', in which case the task will be executed at that determined time

class LimitedIntervalTask(BaseTask):
    execute_at: str
    executions: Union[int, str] = 1  # If value is "*", the task will always be executed at that date, otherwise it will be executed the number of times delimited

    @field_validator('executions')
    def validate_executions(cls, v):
        if isinstance(v, str) and v != "*":
            raise ValueError('executions must be an integer or "*"')
        return v

class IntervalMinutesTask(BaseTask):
    execute_every: int
    

class EveryDayTask(BaseTask):
    execute_at: List[str]  # List of times in 'HH:MM' format

# CRYPTO SCHEDULE
class CryptoAlertTask(BaseTask):
    asset: str
    price_alert: str

# CONFIGURATION
class WholeConfiguration(BaseTask):
    default_time_zone: Optional[str]


# RETURN SCHEMAS
class Return_SON(BaseModel):
    status: Literal["success", "error"]
    task_id: uuid.UUID
    message: str
    timezone: str
