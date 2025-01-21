from functools import wraps
from fastapi import HTTPException
from typing import Optional
from datetime import timedelta, datetime, timezone
from pydantic import BaseModel
import uuid, asyncio

from sqlalchemy import select, update, insert, delete, join, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DBAPIError, NoResultFound
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import UUID

from src.app.security import encrypt_data

from .schemas import *
from .database import async_engine
from .models import *


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
                # except DBAPIError as e:
                #     await session.rollback()
                #     raise HTTPException(status_code=400, detail="There is probably a wrong data type")
    return wrapper


# CRUD Functions

@db_connection
async def create_new_user(session: AsyncSession, username: str, name: Optional[str] = None,
                        email: Optional[str] = None,
                         url_picture: Optional[str] = None):
    """
    Create a new user with the provided details.
    """

    new_user = Users(
        username=username,
        name=name,
        email=email,
        url_picture=url_picture
    )
    session.add(new_user)
    await session.flush()  
    await session.refresh(new_user)  
    return new_user.id


@db_connection
async def add_new_account(session: AsyncSession, user_id: uuid.UUID, account_type: str, email: str, asociated_ip: str):
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
    return str(new_account.id)

@db_connection
async def get_account_id(session: AsyncSession, email: str):
    """
    Returns the account id
    """
    account = await session.execute(
        select(Account).where(Account.email == email)
    )

    res = account.scalar_one_or_none()
    if res:
        return str(res.id)
    else:
        return None

@db_connection
async def check_if_user_exists(session: AsyncSession, email: str):

    """
    Check if user exsits in the database by its email
    """
    result = await session.execute(
        select(Users).where(Users.email == email)
    )
    
    user = result.scalar_one_or_none()

    if not user:
        return None
    else:
        return {
            "user_id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
        }

@db_connection
async def get_all_joined_users(session: AsyncSession):
    result = await session.execute(
        select(Users)
    )

    all_users = result.scalars().all()

    if not all_users:
        return {}
    else:
        registered_users = [
            {"user_id": user.id, "username": user.username, "name": user.name, "surname": user.surname, "email": user.email, "url_picture": user.url_picture, "role": user.role}
            for user in all_users
        ]

        return registered_users



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
async def create_google_oauth(session: AsyncSession, id: str, data: CreateGoogleOAuth):
    """
    Create a new GoogleOAuth record for a user.
    """
    # Verify that the user exists
    result = await session.execute(select(Users).where(Users.id == data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_oauth = GoogleOAuth(
        id=id,
        user_id=data.user_id,
        access_token=data.access_token,
        refresh_token=data.refresh_token,
        expires_at=data.expires_at
    )
    session.add(new_oauth)
    await session.flush()  
    await session.refresh(new_oauth)  
    return new_oauth

@db_connection
async def update_google_oauth(session: AsyncSession, user_id: str, data: UpdateGoogleOAuth):
    """
    Update an existing GoogleOAuth record identified by its user_id.
    If no record is found, returns a 404 error.
    """
    # Fetch the existing record by user_id
    result = await session.execute(
        select(GoogleOAuth).where(GoogleOAuth.user_id == user_id)
    )
    oauth_record = result.scalar_one_or_none()
    if not oauth_record:
        raise HTTPException(status_code=404, detail=f"GoogleOAuth record not found, user_id: {user_id}, data: {data.model_dump_json()}")

    # Update fields if provided
    if data.access_token is not None:
        oauth_record.access_token = data.access_token
    if data.refresh_token is not None:
        oauth_record.refresh_token = data.refresh_token
    if data.expires_at is not None:
        oauth_record.expires_at = data.expires_at

    # Flush changes to the database
    await session.flush()
    await session.refresh(oauth_record)  # Refresh the object with the latest DB state
    
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

@db_connection
async def get_google_credentials(session: AsyncSession, user_id) -> dict:
    """
    Get user credentials by its id
    """
    
    result = await session.execute(select(GoogleOAuth).where(GoogleOAuth.user_id == user_id))
    google_credentials = result.scalar_one_or_none()
    
    if not google_credentials:
        raise HTTPException(status_code=404, detail="Credentials not found")

    return {
        "acces_token": google_credentials.access_token,
        "refresh_token": google_credentials.refresh_token,
        "user_id": google_credentials.user_id
    }

@db_connection
async def get_user_profile(session: AsyncSession, user_id) -> dict:
    """Get user profile by its id"""
    result = await session.execute(select(Users).where(Users.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        return {
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "url_picture": user.url_picture,
            "role": user.role
        }
    else:
        raise HTTPException(status_code=404, detail="User not found")

@db_connection
async def update_profile(session: AsyncSession, email: str, user_update: UpdateProfileUpdate):
    """Update user profile"""
    
    #  Get the user_id based on email
    user = await session.execute(
        select(Users.id)
        .where(Users.email == email)
    )
    user_id = user.scalar()

    if not user_id:
        return 0 
    
    # Check if the name and surname can be updated (if oauth_synced is True)
    result_updatable = await session.execute(
        select(UserConfiguration.oauth_synced)
        .where(UserConfiguration.user_id == user_id)
    )
    
    oauth_synced = result_updatable.scalar()

    # Only update the name and surname if oauth_synced is True
    if oauth_synced:
        result = await session.execute(
            update(Users)
            .where(Users.id == user_id)
            .values(
                name=user_update.name,
                username=user_update.username,
                url_picture=user_update.url_picture
            )
            .execution_options(synchronize_session="fetch")
        )
        
        await session.commit()
        return result.rowcount
    
    return 0


@db_connection
async def get_joined_users(session: AsyncSession, limit: int):
    """Get all joined users on this platform (administrative function)"""
    result = await session.execute(
        select(Users).order_by(Users.joined_at.desc()).limit(limit)
    )
    users = result.scalars().all()
    
    joined_users = [
        {"user_id": user.id, "username": user.username, "name": user.name, "surname": user.surname, "email": user.email, "url_picture": user.url_picture, "role": user.role, "joined_at": user.joined_at}

        for user in users
    ]

    return joined_users

@db_connection
async def delete_public_email(session: AsyncSession, user_id):
    """Delete public email from user id as well as handle all its exceptions"""
    result = await session.execute(
        select(UserConfiguration)
        .where(UserConfiguration.user_id == user_id)
    )
    user_config = result.scalars().first()

    if user_config is None:
        return "not modified"  

    if user_config.public_email is None:
        return "not modified"

    await session.execute(
        update(UserConfiguration)
        .where(UserConfiguration.user_id == user_id)
        .values(public_email=None)
    )
    await session.commit()
    return "deleted"


@db_connection
async def set_public_email(session: AsyncSession, user_id: int, public_email: str | None):
    """Set public email"""
    # Check if the user exists
    result = await session.execute(
        select(UserConfiguration).where(UserConfiguration.user_id == user_id)
    )
    user_config = result.scalars().first()

    if user_config is None:
        raise HTTPException(status_code=404, detail="User not found")

    # If public_email is None, we don't update it
    if public_email is not None:
        # Proceed to update the public_email if user exists
        await session.execute(
            update(UserConfiguration)
            .where(UserConfiguration.user_id == user_id)
            .values(public_email=public_email)
        )
        await session.commit()

    return {"message": "Public email updated" if public_email else "No email updated"}

    

# USER CONFIGURATION TABLE
@db_connection
async def get_users_sorted_by_joined_at(session: AsyncSession):
    result = await session.execute(
        select(Users)
        .order_by(Users.joined_at.desc())
    )
    return result.scalars().all()


@db_connection
async def createDefaultConfiguration(session: AsyncSession, user_id: str):
    """Create default configuration for the user"""
    default_configuration = UserConfiguration(
        user_id = user_id,
        oauth_synced = True,
        picture_synced = True,
        dark_mode = True,
        currency = "usd",
        language = "en",
        notifications = "recent",
    )

    session.add(default_configuration)
    await session.commit()


@db_connection
async def get_accounts(session: AsyncSession, user_id: str):
    """Get user accounts"""
    result = await session.execute(
        select(Account)
        .where(Account.user_id == user_id)
    )

    result = result.scalars().all()

    accounts = [{"id": account.account_id, "proxy_ip": account.proxy_ip, "account_name": account.account_name} for account in result] 
    return accounts

@db_connection
async def setUserConf(session: AsyncSession, user_id: str, user_settings: PreferencesBase):
    try:
        uuid_obj = uuid.UUID(user_settings, version=4)
        stmt_select = select(UserConfiguration).where(UserConfiguration.user_id == uuid_obj)
        result = await session.execute(stmt_select)
        user_configurtion_row = result.scalar()

        if user_configurtion_row:
            stmt_update = (
                update(UserConfiguration)
                .where(UserConfiguration.user_id == uuid_obj)
                .values(
                    username=user_settings.username,
                    name=user_settings.name,
                    avariable_emails=user_settings.avariable_emails
                )
            )


    except ValueError:
         raise HTTPException(status_code=400, detail=f"Error: {user_id} is not a valid UUID4")



@db_connection
async def set_user_base_config(session: AsyncSession, user_config: PreferencesBase, user_id: str):
    try:
        # Ensure the user_id is a valid UUID4
        uuid_obj = uuid.UUID(user_id, version=4)

        # Try to fetch the existing configuration for the user
        stmt_select = select(UserConfiguration).where(UserConfiguration.user_id == uuid_obj)
        result = await session.execute(stmt_select)
        user_config_row = result.scalar()


        # check whether create or update
        if user_config_row:
            stmt_update = (
                update(UserConfiguration)
                .where(UserConfiguration.user_id == uuid_obj)
                .values(
                    dark_mode=user_config.dark_mode,
                    currency=user_config.currency,
                    language=user_config.language,
                    notifications=user_config.notifications,
                )
            )
            await session.execute(stmt_update)
        else:
            # Insert new configuration
            new_user_config = UserConfiguration(
                user_id=uuid_obj,
                dark_mode=user_config.dark_mode,
                currency=user_config.currency,
                language=user_config.language,
                notifications=user_config.notifications,
            )
            session.add(new_user_config)

        # Commit changes
        await session.commit()

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Error: {user_id} is not a valid UUID4")

    except NoResultFound as e:
        print(f"Error: {str(e)}")
        await session.rollback()


@db_connection
async def get_whole_user(session: AsyncSession, user_id: str):

    uuid_obj = uuid.UUID(user_id, version=4)

    # Query by user_id in UserConfiguration
    result1 = await session.execute(
        select(UserConfiguration)
        .where(UserConfiguration.user_id == uuid_obj)
    )

    result2 = await session.execute(
        select(Users)
        .where(Users.id == uuid_obj)
    )

    result3 = await session.execute(
        select(Account)
        .where(Account.user_id == user_id)
    )

    user_profile = result1.scalar_one_or_none()
    user_data = result2.scalar_one_or_none()
    user_accounts = result3.scalars().all()

    # Get user email and all its accounts emails
    user_emails = [user_data.email]

    if len(user_accounts) <= 1:
        account_emails = [acc.email for acc in user_accounts]
        for email in account_emails:
            if email not in user_emails: 
                user_emails.append(email)
  

    if not user_profile and not user_data:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {
        "username": user_data.username,
        "name": user_data.name,
        "email": user_data.email,
        "url_picture": user_data.url_picture,
        "client_timezone": user_profile.client_timezone if user_profile else None,
        "dark_mode": user_profile.dark_mode if user_profile else None,
        "currency": user_profile.currency if user_profile else None,
        "language": user_profile.language if user_profile else None,
        "notifications": user_profile.notifications if user_profile else None,
        "avariable_emails": user_emails
    }

@db_connection
async def delete_user_account(session: AsyncSession, user_id: str):
    all_accounts = await get_all_accounts(user_id=user_id)

    # Delete all asociated accounts
    await asyncio.gather(*(delete_account(account_id=account["account_id"]) for account in all_accounts))

    # Delete user data
    deletion_tasks = [
        session.execute(delete(UserConfiguration).where(UserConfiguration.user_id == user_id)),
        session.execute(delete(GoogleOAuth).where(GoogleOAuth.user_id == user_id)),
        session.execute(delete(StarredCryptos).where(StarredCryptos.user_id == user_id)),
        session.execute(delete(HistoricalSearchedCryptos).where(HistoricalSearchedCryptos.user_id == user_id)),
        # session.execute(delete(MonthlySubscription).where(MonthlySubscription.user_id == user_id)),
    ]
    await asyncio.gather(*deletion_tasks)

    # Delete user record and commit
    await session.execute(delete(Users).where(Users.id == user_id))
    await session.commit()

    return 200

# - - - - USER HISTORICAL SEARCH - - - - - 
@db_connection
async def add_new_searched_crypto(session: AsyncSession, user_id: str, symbol: str, name: str, picture_url: str):
    try:
        # Validate the user_id as a UUID
        try:
            uuid_obj = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format for user_id: {user_id}")

        # Fetch the number of existing records for the user
        result = await session.execute(
            select(HistoricalSearchedCryptos)
            .where(HistoricalSearchedCryptos.user_id == uuid_obj)
            .order_by(HistoricalSearchedCryptos.searchet_at.asc())  
        )

        cryptos = result.scalars().all()

        # Check if the user already has 20 records
        if len(cryptos) >= 20:
            oldest_crypto = cryptos[0]
            await session.delete(oldest_crypto)
            await session.flush()  

        # Dekete repeated crypto
        for crypto in cryptos:
            if crypto.searched_symbol == symbol:
                await session.delete(crypto)
                await session.flush()

        # Add the new record
        new_searched_crypto = HistoricalSearchedCryptos(
            user_id=uuid_obj,
            searched_symbol=symbol,
            name=name,
            picture_url=picture_url
        )

        session.add(new_searched_crypto)
        await session.flush()
        await session.refresh(new_searched_crypto)

    except DBAPIError as e:
        # Handle database-related errors
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@db_connection
async def get_searched_cryptos(session: AsyncSession, user_id: str):
    try:
        # Validate the user_id as a UUID
        try:
            uuid_obj = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format for user_id: {user_id}")

        result = await session.execute(
            select(HistoricalSearchedCryptos)
            .where(HistoricalSearchedCryptos.user_id == uuid_obj)
            .order_by(HistoricalSearchedCryptos.searched_at.desc())
        )
        
        cryptos = result.scalars().all()

        if not cryptos:
            return []

        cryptos_data = [
            {"id": crypto.id, "symbol": crypto.searched_symbol, "name": crypto.name, "picture_url": crypto.picture_url} 
            for crypto in cryptos
        ]

        return cryptos_data

    except DBAPIError as e:
        # Handle database-related errors
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@db_connection
async def delete_searched_crypto(session: AsyncSession, id: str) -> None:
    try:
        # Validate if the id is a valid UUID
        try:
            uuid_obj = uuid.UUID(id) 
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {id}")

        # Proceed with the query if the UUID is valid
        result = await session.execute(
            select(HistoricalSearchedCryptos)
            .where(HistoricalSearchedCryptos.id == uuid_obj)
        )
        searched_crypto = result.scalar_one_or_none()

        if not searched_crypto:
            raise HTTPException(status_code=404, detail=f"Searched crypto with id {id} not found.")

        await session.delete(searched_crypto)
        await session.commit()

    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"Searched crypto with id {id} not found.")

    except DBAPIError as e:
        # Handle DB-related errors
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@db_connection
async def set_new_user_credentials(session: AsyncSession, account_id: str, apikey, secret_key, passphrase):
    """Create or Update user credentials for Bitget"""
    
    # Ensure account_id is a valid UUID string
    try:
        uuid_account_id = uuid.UUID(account_id) 
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {account_id}")
    
    # Query with explicit casting to UUID
    result = await session.execute(
        select(UserCredentials).where(cast(UserCredentials.account_id, UUID) == uuid_account_id)
    )
    
    user_credentials = result.scalars().first()

    if user_credentials:
        # Update existing credentials
        user_credentials.set_encrypted_apikey(encrypt_data(apikey))
        user_credentials.set_encrypted_secret_key(encrypt_data(secret_key))
        user_credentials.set_encrypted_passphrase(encrypt_data(passphrase))
        operation = "updated"
    else:
        # Decode Base64 and assign raw bytes
        user_credentials = UserCredentials(
            account_id=uuid_account_id,
            encrypted_apikey=base64.b64decode(encrypt_data(apikey).encode('utf-8')),
            encrypted_secret_key=base64.b64decode(encrypt_data(secret_key).encode('utf-8')),
            encrypted_passphrase=base64.b64decode(encrypt_data(passphrase).encode('utf-8'))
        )
        session.add(user_credentials)
        operation = "created"


    # Commit the transaction
    await session.commit()

    return {"status": "success", "message": f"Credentials {operation} successfully.", "operation": operation}

@db_connection
async def get_account_credentials(session: AsyncSession):
    pass

# - - - ACCOUNTS - - - 
@db_connection
async def get_all_accounts(session: AsyncSession, user_id: str):
    """Save trading account"""

    # Check if the trading account doesn't have the 
    try:
        result = await session.execute(
            select(Account)
            .where(
                Account.user_id == user_id,
            )
        )
    except DBAPIError:
        raise HTTPException(status_code=404, detail="User not found")

    accounts = result.scalars().all()

    if accounts:
        all_trading_accounts = [{"account_id": res.account_id, "account_name": res.account_name, "type": res.type, "email": res.email, "proxy_ip": res.proxy_ip} for res in accounts]
        return all_trading_accounts
    else:
        return []
    
@db_connection
async def set_trading_account(session: AsyncSession, user_id: str, account_id: str) -> int:
    """Set trading account as main, or turn all accounts into sub-accounts if account_id is None."""

    accounts = await get_all_accounts(user_id=user_id) 

    if not accounts:
        return 404 
    try:
        if account_id is None:
            await session.execute(
                update(Account)
                .where(Account.user_id == user_id)  
                .values(type='sub-account')
            )
            await session.commit()
            return 200

        for account in accounts:
            if account['type'] == 'main' and account_id != account['account_id']:
                await session.execute(
                    update(Account)
                    .where(Account.account_id == account['account_id'])  
                    .values(type='sub-account')
                )

        result = await session.execute(
            update(Account)
            .where(Account.account_id == account_id)  
            .values(type='main-account')
        )

        if result.rowcount == 0:
            await session.rollback()  
            return 404

        await session.commit()
        return 200

    except Exception as e:
        print(f"Error during account update: {e}")
        await session.rollback()
        raise

@db_connection
async def delete_account(session: AsyncSession, account_id: str):
    # Delete credentials
    await session.execute(
        delete(UserCredentials)
        .where(UserCredentials.account_id == account_id)
    )    

    # Delete Risk Management
    await session.execute(
        delete(RiskManagement)
        .where(RiskManagement.account_id == account_id)
    )

    # Dete historical PNL
    await session.execute(
        delete(Historical_PNL)
        .where(Historical_PNL.account_id == account_id)
    )

    # Delete account
    await session.execute(
        delete(Account)
        .where(Account.account_id == account_id)
    )
    

@db_connection
async def get_main_trading_account(session: AsyncSession, user_id):
    """Select main trading account"""
    result = await session.execute(
        select(Account)
        .where(
            and_(
                Account.user_id == user_id,
                Account.type == 'main-account'
            )
        )
    )

    main_trading_account = result.scalar_one_or_none()

    if not main_trading_account:
        return None
    
    return {"account_id": main_trading_account.account_id, "account_name": main_trading_account.account_name, "type": main_trading_account.type, "email": main_trading_account.email, "proxy_id": main_trading_account.proxy_ip}


# STARRED CRYPTOS

@db_connection
async def add_new_starred_crypto(session: AsyncSession, user_id: str, symbol: str, name: str, picture_url: str):
    try:

        try:
            uuid_obj = uuid.UUID(user_id) 
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {id}")

        new_starred_cypro = StarredCryptos(
            user_id=uuid_obj,
            symbol=symbol,
            name=name,
            picture_url=picture_url
        )

        session.add(new_starred_cypro)
        await session.commit()
        
    except DBAPIError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@db_connection
async def is_starred_crypto(session: AsyncSession, user_id: str, symbol: str) -> bool:
    """Checks whether it' starred crypto or not"""
    result = await session.execute(
        select(StarredCryptos)
        .where(and_(StarredCryptos.user_id == user_id, StarredCryptos.symbol == symbol))
    )

    if not result.scalar_one_or_none():
        return False
    else:
        return True


@db_connection
async def delete_starred_crypto(session: AsyncSession, user_id: str, symbol: str):
    """Removes a crypto from the database by a given user_id and symbol"""
    try:
        # Ensure that the user_id is a valid UUID
        uuid_obj = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {user_id}")

    try:
        # Query the StarredCryptos table by user_id and symbol
        result = await session.execute(
            select(StarredCryptos)
            .where(and_(StarredCryptos.user_id == uuid_obj, StarredCryptos.symbol == symbol))
        )

        starred_crypto = result.scalar_one_or_none()
    except DBAPIError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


    if not starred_crypto:
        raise HTTPException(status_code=404, detail=f"Crypto {symbol} not found for user {user_id}")
    
    # Delete the crypto if found
    await session.delete(starred_crypto)
    await session.commit()  

    return {"response": "Starred crypto removed successfully"}


async def main_tesings():
   
    res = await get_all_accounts("49898f05-bc00-4d4b-87fd12885b8cf28"); print("all account -> ",res)
    res2 = await delete_user_account("49898f05-bc00-4d4b-87fd-212885b8cf28")

if __name__ == "__main__":
    asyncio.run(main_tesings())