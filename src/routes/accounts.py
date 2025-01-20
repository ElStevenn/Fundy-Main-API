# routers/accounts.py

from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List
from src.app import schemas
from src.app.database import crud
from src.app import schemas as dbschemas
from src.app.security import get_current_credentials
from typing import Annotated
import uuid

accounts_router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"]
)


@accounts_router.get("/users", description="### Get all the associated accounts to a user\n\nThese accounts can be both trading or sub-accounts",response_model=List[dict],)
async def get_user_accounts(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials
    user_accounts = await crud.get_all_accounts(user_id=user_id)
    return user_accounts


@accounts_router.get("/main-account",description="### Retrieve the main trading account associated with the user",)
async def get_main_trading_account(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials
    main_trading_account = await crud.get_main_trading_account(user_id=user_id)
    return {"main_trading_account": main_trading_account}

"""
@accounts_router.get("/configuration", description="### Get accounts configuration\n\nAt this moment the only feature is to get the **main trading account**")
async def get_accounts_configuration(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_body: schemas.UserConfProfile):
    _, user_id = user_credentials
     # Validate UUIDset-profile-configuration

    try:
        uuid_obj = uuid.UUID(user_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Error: {user_id} is not a valid UUID4")

    # Update user profile
    await crud.setUserProfileBase(name=request_body.name, user_id=user_id)

    # Create UserBaseConfig instance to update configuration
    user_config = dbschemas.PreferencesSettings(
        email_configuration
    )

    await crud.set_user_base_config(user_config=user_config, user_id=user_id)

    if not request_body.public_email:
        await crud.delete_public_email(user_id=user_id)
    else:
        await crud.set_public_email(user_id=user_id, public_email=request_body.public_email)

    return {"success": True, "message": "User profile updated successfully"}
"""



@accounts_router.post("/configuration", description="### Save accounts configuration\n\nAt this moment the only feature is to save the **main trading account**",)
async def set_main_trading_account(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_body: schemas.AccountSaveConfig):
    _, user_id = user_credentials

    # Set main trading account
    response = await crud.set_trading_account(account_id=request_body.account_id, user_id=user_id)

    return Response(status_code=response)

@accounts_router.delete("/{account_id}", description="### Delete an associated exchange account",)
async def delete_account(account_id: str,):
    await crud.delete_account(account_id=account_id)
    return Response(status_code=204)
