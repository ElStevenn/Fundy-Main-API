# routers/accounts.py

from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List
from src.app import schemas
from src.app.database import crud
from src.app.security import get_current_credentials
from typing import Annotated

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


@accounts_router.post("/configuration", description="### Save accounts configuration\n\nAt this moment the only feature is to save the **main trading account**",)
async def set_main_trading_account(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_body: schemas.AccountSaveConfig,):
    _, user_id = user_credentials

    # Set main trading account
    response = await crud.set_trading_account(account_id=request_body.account_id, user_id=user_id)

    return Response(status_code=response)

@accounts_router.delete("/{account_id}", description="### Delete an associated exchange account",)
async def delete_account(account_id: str,):
    await crud.delete_account(account_id=account_id)
    return Response(status_code=204)
