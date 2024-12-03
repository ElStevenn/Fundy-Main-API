from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
from typing import Dict, Any, Optional, List, Union, Literal, Self
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
    interval_minutes: int
    
class DatetimeTask(BaseTask):
    task_datetime: datetime

class EveryDayTask(BaseTask):
    execute_at: List[str]  # List of times in 'HH:MM' format


class UserBase(BaseModel):
    name: str
    surname: str

class UserConfProfile(UserBase):
    webpage_url: Optional[str] = None
    public_email: Optional[str] = None
    bio: Optional[str] = None
    main_used_exchange: Optional[str] = None
    trading_experience: Optional[str] = None
    location: Optional[str] = None

class CryptoSearch(BaseModel):
    symbol: str
    name: str
    picture_url: str


# CRYPTO SCHEDULE
class CryptoAlertTask(BaseTask):
    asset: str
    price_alert: str

# CONFIGURATION
class WholeConfiguration(BaseTask):
    default_time_zone: Optional[str]

class UserCredentials(BaseModel):
    email: EmailStr
    apikey: str
    secret_key: str
    passphrase: str
    
class UserAccount(BaseModel):
    type: str
    email: EmailStr

class AccountSaveConfig(BaseModel):
    account_id: Optional[str] = None

# RETURN SCHEMAS
class Return_SON(BaseModel):
    status: Literal["success", "error"]
    task_id: uuid.UUID
    message: str
    timezone: str

class UserResponse(BaseModel):
    user_id: uuid.UUID
    username: str | None
    name: str | None
    surname: str | None
    email: EmailStr | None
    url_picture: str | None
    role: str 
    joined_at: datetime | None

    class Config:
        orm_mode = True

# DELETE THIS
class OpenOrderTest(BaseModel):
    symbol: str
    mode: Literal['long', 'short']
    open_order_in: int
    close_order_in: int

