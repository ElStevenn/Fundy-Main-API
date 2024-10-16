from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid

class CreateGoogleOAuth(BaseModel):
    user_id: uuid.UUID = Field(..., description="UUID of the user")
    access_token: str = Field(..., description="Access token obtained from Google OAuth")
    refresh_token: str = Field(..., description="Refresh token obtained from Google OAuth")
    expires_at: datetime = Field(..., description="Expiration datetime of the access token")

class UpdateGoogleOAuth(BaseModel):
    access_token: Optional[str] = Field(None, description="Updated access token")
    refresh_token: Optional[str] = Field(None, description="Updated refresh token")
    expires_at: Optional[datetime] = Field(None, description="Updated expiration datetime of the access token")

class UpdateProfileUpdate(BaseModel):
    name: Optional[str]
    surname: Optional[str]
    url_picture: Optional[str]

class CreateHistoricalPNL(BaseModel):
    # Important Data
    id: str  # Assuming this is the account ID
    symbol: str
    operation_datetime: datetime

    # Secondary Data
    pnl: str
    avg_entry_price: str
    side: Literal['long', 'short']
    closed_value: str

    # Irrelevant data
    opening_fee: str
    closing_fee: str
    net_profits: str

class UserBaseConfig(BaseModel):
    webpage_url: Optional[str] = None
    bio: Optional[str] = None
    main_used_exchange: Optional[str] = None
    trading_experience: Optional[str] = None
    location: Optional[str] = None
    