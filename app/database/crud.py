from .database import async_engine
from .models import *
from sqlalchemy import select, update, insert, delete, join
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DBAPIError
from fastapi import HTTPException
from typing import List, Literal, Optional
from datetime import timedelta, datetime, timezone
from pydantic import BaseModel


def db_connection(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with AsyncSession(async_engine) as session:
            async with session.begin():
                try:                
                    result = await func(session, *args, **kwargs)
    
                    return result
                except OSError:
                    return {"status": "error", "error": "DB connection in the server does not work, maybe the container is not running or IP is wrong since you've restarted the node"}
                except Exception as e:
                    print("An error occurred:", e)
                    raise
    return wrapper


# Mini schemas
class CreateHistoricalPNL(BaseModel):
    # Important Data
    id: str
    symbol: str
    operation_datetime: datetime

    # Secondary Data
    pnl: str
    avg_entry_price: str
    side: Literal['long', 'short']
    closed_value: str

    # Irelevant data
    opening_fee: str
    closing_fee: str
    net_profits: str



# Needed CRUD with our models

@db_connection
async def create_new_user(session: AsyncSession, username):
    pass


@db_connection
async def add_new_account(session: AsyncSession, user_id, type, email):
    pass


@db_connection
async def delete_account_cascade(session: AsyncSession, email, type):
    """Delete account in casaca, which means that all its realized PNL history will be deleted as well"""
    pass

async def create_new_historical_pnl(session: AsyncSession, data: CreateHistoricalPNL):
    """Create new PNL register"""
    pass





