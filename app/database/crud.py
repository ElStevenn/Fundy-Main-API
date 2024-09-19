from .database import async_engine
from .models import *
from sqlalchemy import select, update, insert, delete, join
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DBAPIError
from fastapi import HTTPException
from typing import Optional
from datetime import timedelta, datetime, timezone
from pydantic import BaseModel
from .schemas import *
import uuid


def db_connection(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with AsyncSession(async_engine) as session:
            async with session.begin():
                try:
                    result = await func(session, *args, **kwargs)
                    return result
                except OSError:
                    raise HTTPException(
                        status_code=503,
                        detail="DB connection in the server does not work, maybe the container is not running or IP is wrong since you've restarted the node",
                    )
                except IntegrityError as e:
                    await session.rollback()
                    raise HTTPException(status_code=400, detail=str(e))
                except DBAPIError as e:
                    await session.rollback()
                    raise HTTPException(status_code=500, detail="Database error")
                except Exception as e:
                    await session.rollback()
                    print("An error occurred:", e)
                    raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper


# CRUD Functions

@db_connection
async def create_new_user(session: AsyncSession, username: str, name: Optional[str] = None,
                         surname: Optional[str] = None, email: Optional[str] = None,
                         url_picture: Optional[str] = None):
    """
    Create a new user with the provided details.
    """
    new_user = Users(
        username=username,
        name=name,
        surname=surname,
        email=email,
        url_picture=url_picture
    )
    session.add(new_user)
    await session.flush()  # Flush to assign an ID
    await session.refresh(new_user)  # Refresh to get updated fields
    return new_user


@db_connection
async def add_new_account(session: AsyncSession, user_id: uuid.UUID, account_type: str, email: str):
    """
    Add a new account for the specified user.
    """
    # Generate a unique ID for the account if not provided
    account_id = str(uuid.uuid4())

    # Check if the user exists
    result = await session.execute(select(Users).where(Users.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_account = Account(
        id=account_id,
        type=account_type,
        email=email,
        user_id=user_id
    )
    session.add(new_account)
    await session.flush()
    await session.refresh(new_account)
    return new_account


@db_connection
async def delete_account_cascade(session: AsyncSession, email: str, account_type: str):
    """
    Delete an account by email and type. This will cascade delete all related Historical_PNL records.
    """
    # Fetch the account
    result = await session.execute(
        select(Account).where(Account.email == email, Account.type == account_type)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Delete the account; cascading will handle related Historical_PNL
    await session.delete(account)
    return {"status": "success", "detail": "Account and related PNL records deleted successfully"}


@db_connection
async def create_new_historical_pnl(session: AsyncSession, data: CreateHistoricalPNL):
    """
    Create a new Historical_PNL record based on the provided data.
    """
    # Ensure the account exists
    result = await session.execute(
        select(Account).where(Account.id == data.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    new_pnl = Historical_PNL(
        id=uuid.uuid4(),
        symbol=data.symbol,
        operation_datetime=data.operation_datetime,
        pnl=float(data.pnl),
        avg_entry_price=float(data.avg_entry_price),
        side=data.side,
        closed_value=float(data.closed_value),
        opening_fee=float(data.opening_fee),
        closing_fee=float(data.closing_fee),
        net_profits=float(data.net_profits),
        account_id=account.id
    )
    session.add(new_pnl)
    await session.flush()
    await session.refresh(new_pnl)
    return new_pnl


@db_connection
async def create_google_oauth(session: AsyncSession, data: CreateGoogleOAuth):
    """
    Create a new GoogleOAuth record for a user.
    """
    # Verify that the user exists
    result = await session.execute(select(Users).where(Users.id == data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_oauth = GoogleOAuth(
        user_id=data.user_id,
        access_token=data.access_token,
        refresh_token=data.refresh_token,
        expires_at=data.expires_at
    )
    session.add(new_oauth)
    await session.flush()  # Assigns an ID
    await session.refresh(new_oauth)  # Refresh to get updated fields
    return new_oauth

@db_connection
async def update_google_oauth(session: AsyncSession, oauth_id: int, data: UpdateGoogleOAuth):
    """
    Update an existing GoogleOAuth record identified by its ID.
    """
    # Fetch the existing record
    result = await session.execute(select(GoogleOAuth).where(GoogleOAuth.id == oauth_id))
    oauth_record = result.scalar_one_or_none()
    if not oauth_record:
        raise HTTPException(status_code=404, detail="GoogleOAuth record not found")

    # Update fields if provided
    if data.access_token is not None:
        oauth_record.access_token = data.access_token
    if data.refresh_token is not None:
        oauth_record.refresh_token = data.refresh_token
    if data.expires_at is not None:
        oauth_record.expires_at = data.expires_at

    session.add(oauth_record)
    await session.flush()
    await session.refresh(oauth_record)
    return oauth_record

@db_connection
async def delete_google_oauth(session: AsyncSession, oauth_id: int):
    """
    Delete a GoogleOAuth record identified by its ID.
    """
    # Fetch the record to delete
    result = await session.execute(select(GoogleOAuth).where(GoogleOAuth.id == oauth_id))
    oauth_record = result.scalar_one_or_none()
    if not oauth_record:
        raise HTTPException(status_code=404, detail="GoogleOAuth record not found")

    await session.delete(oauth_record)
    return {"status": "success", "detail": f"GoogleOAuth record with ID {oauth_id} deleted successfully."}


