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

class UpdateUserConf(BaseModel):
    minium_funding_rate_to_show: Optional[str] = None
    user_exchange: Optional[str] = None

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
    account_id: str
    encrypted_apikey: bytes = Field(..., alias='encrypted_apikey')
    encrypted_secret_key: bytes = Field(..., alias='encrypted_secret_key') 
    encrypted_passphrase: bytes = Field(..., alias='encrypted_passphrase')

    # Custom setters to convert from bytes to string
    @classmethod
    def from_strings(cls, encrypted_apikey: str, encrypted_secret_key: str, encrypted_passphrase: str) -> 'UserCredentials':
        return cls(
            encrypted_apikey=encrypted_apikey.encode('utf-8'),
            encrypted_secret_key=encrypted_secret_key.encode('utf-8'),
            encrypted_passphrase=encrypted_passphrase.encode('utf-8')
        )

    # Optionally, if you need to retrieve as strings
    def to_strings(self) -> dict[str, str]:
        return {
            'encrypted_apikey': self.encrypted_apikey.decode('utf-8'),
            'encrypted_secret_key': self.encrypted_secret_key.decode('utf-8'),
            'encrypted_passphrase': self.encrypted_passphrase.decode('utf-8'),
        }
    
class UserAccount(BaseModel):
    type: str
    email: str

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

