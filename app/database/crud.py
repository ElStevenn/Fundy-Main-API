from .database import async_engine
from .models import *
from sqlalchemy import select, update, insert, delete, join, and_
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DBAPIError, NoResultFound
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import UUID
from fastapi import HTTPException
from typing import Optional
from datetime import timedelta, datetime, timezone
from pydantic import BaseModel
from .schemas import *
import uuid, asyncio


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
    await session.flush()  
    await session.refresh(new_user)  
    return new_user.id


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
            "surname": user.surname,
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
async def update_google_oauth(session: AsyncSession, oauth_id: str, data: UpdateGoogleOAuth):
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

    # No need to re-add since the object is already tracked
    await session.flush()  # You can even try removing this if errors persist
    await session.refresh(oauth_record)  # Optionally ensure it's refreshed
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
            "surname": user.surname,
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
                surname=user_update.surname,
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
        min_funding_rate_threshold = 0.1,
        oauth_synced = True,
        picture_synced = True
    )

    session.add(default_configuration)
    await session.commit()


@db_connection
async def setUserProfileBase(session: AsyncSession, name: str, surname: str, user_id: str):
    try:
        # Query current values
        existing_user = await session.get(Users, user_id)
        stmt = (
            update(Users)
            .where(Users.id == user_id)
            .values(
                name=name,
                surname=surname
            )
        )
        await session.execute(stmt)
        
        # If name or surname are different, set oauth_synced to False in UserConfiguration
        if existing_user.name != name or existing_user.surname != surname:
            oauth_stmt = (
                update(UserConfiguration)
                .where(UserConfiguration.user_id == user_id)
                .values(oauth_synced=False)
            )
            await session.execute(oauth_stmt)

        await session.commit()

    except ValueError:
         raise HTTPException(status_code=400, detail=f"Error: {user_id} is not a valid UUID4")



@db_connection
async def set_user_base_config(session: AsyncSession, user_config: UserBaseConfig, user_id: str):
    try:
        # Ensure the user_id is a valid UUID4
        uuid_obj = uuid.UUID(user_id, version=4)

        # Try to fetch the existing configuration for the user
        stmt_select = select(UserConfiguration).where(UserConfiguration.user_id == uuid_obj)
        result = await session.execute(stmt_select)
        user_config_row = result.scalar()


        # Ensure that the Name and Surname are the same, otherwise the boolean 'oauth_synced' will be false




        # check whether create or update
        if user_config_row:
            stmt_update = (
                update(UserConfiguration)
                .where(UserConfiguration.user_id == uuid_obj)
                .values(
                    webpage_url=user_config.webpage_url,
                    location=user_config.location,
                    bio=user_config.bio,
                    main_used_exchange=user_config.main_used_exchange,
                    trading_experience=user_config.trading_experience
                )
            )
            await session.execute(stmt_update)
        else:
            # Insert new configuration
            new_user_config = UserConfiguration(
                user_id=uuid_obj,
                webpage_url=user_config.webpage_url,
                location=user_config.location,
                bio=user_config.bio,
                main_used_exchange=user_config.main_used_exchange,
                trading_experience=user_config.trading_experience
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

    user_profile = result1.scalar_one_or_none()
    user_data = result2.scalar_one_or_none()

    if not user_profile and not user_data:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {
        "username": user_data.username,
        "name": user_data.name,
        "surname": user_data.surname,
        "email": user_data.email,
        "url_picture": user_data.url_picture,
        "client_timezone": user_profile.client_timezone if user_profile else None,
        "min_funding_rate_threshold": user_profile.min_funding_rate_threshold if user_profile else None,
        "location": user_profile.location if user_profile else None,
        "bio": user_profile.bio if user_profile else None,
        "webpage_url": user_profile.webpage_url if user_profile else None,
        "trading_experience": user_profile.trading_experience if user_profile else None,
        "main_used_exchange": user_profile.main_used_exchange if user_profile else None
    }


# USER HISTORICAL SEARCH
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
            .order_by(HistoricalSearchedCryptos.searchet_at.desc())
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
async def create_new_account(session: AsyncSession, user_id, email: str, type: str):
    """Creates a new account"""
    
    new_account = Account(type=type, email=email, user_id=user_id)
    session.add(new_account)
    await session.commit()


@db_connection
async def set_new_user_credentials(session: AsyncSession, account_id: str, encrypted_apikey, encrypted_secret_key, encrypted_passphrase):
    """Create or Update user credentials for Bitget"""
    
    # Ensure account_id is a valid UUID string
    try:
        uuid_account_id = uuid.UUID(account_id)  # Convert to UUID for comparison
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {account_id}")
    
    # Query with explicit casting to UUID
    result = await session.execute(
        select(UserCredentials).where(cast(UserCredentials.account_id, UUID) == uuid_account_id)
    )
    
    user_credentials = result.scalars().first()

    if user_credentials:
        user_credentials.set_encrypted_apikey(encrypted_apikey)
        user_credentials.set_encrypted_secret_key(encrypted_secret_key)
        user_credentials.set_encrypted_passphrase(encrypted_passphrase)
        operation = "updated"
    else:
        user_credentials = UserCredentials(
            account_id=uuid_account_id,
            encrypted_apikey=encrypted_apikey,
            encrypted_secret_key=encrypted_secret_key,
            encrypted_passphrase=encrypted_passphrase
        )
        session.add(user_credentials)
        operation = "created"

    # Commit the transaction
    await session.commit()

    return {"status": "success", "message": f"Credentials {operation} successfully.", "operation": operation}


@db_connection
async def get_list_id_accounts(session: AsyncSession, user_id: str):
    """Get all accounts for a given user_id"""

  
    try:
        user_uuid = uuid.UUID(user_id)  
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid user_id: {user_id}")

    try:
        # Perform the query to fetch accounts by user_id
        result = await session.execute(
            select(Account).where(Account.user_id == user_uuid)
        )
        accounts = result.scalars().all()

        # If no accounts found, raise a 404 error
        if not accounts:
            raise HTTPException(status_code=404, detail=f"No accounts found for user_id: {user_id}")

        # Format the results as a list of dictionaries
        account_data = [
            {"account_id": acc.id, "type": acc.type, "email": acc.email} 
            for acc in accounts
        ]

        return account_data

    except Exception as e:
        # Raise a detailed error message for debugging
        raise HTTPException(status_code=404, detail=str(e))

  
    

@db_connection
async def get_account_credentials(session: AsyncSession):
    pass


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
    await session.commit()  # Commit after deletion

    return {"response": "Starred crypto removed successfully"}


async def main_tesings():
    # await add_new_searched_crypto("118c056f-e19e-4267-8a1d-68947ae08559", "BTCUSDT", "Bitcoin", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Bitcoin.svg/1200px-Bitcoin.svg.png")
    res = await get_list_id_accounts("4e21db51-0e4d-47e2-bfc0-15ad00cb6c61")
    print("pretty result -> ",res)

if __name__ == "__main__":
    asyncio.run(main_tesings())