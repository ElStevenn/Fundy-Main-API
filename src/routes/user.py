from fastapi import APIRouter, Depends, HTTPException, UploadFile, Response
from typing import List
from src.app import schemas
from src.app.database import crud
from src.app.security import get_current_credentials
from src.app.database import schemas as dbschemas
from fastapi.responses import JSONResponse
from typing import Annotated
import uuid

from src.app.security import encode_session_token, decode_session_token

from src.config import FRONTEND_IP

user_router = APIRouter(
    prefix="/user",
    tags=["User"]
)


@user_router.get("/profile", description="### Get perfile user data:\n\n - **Name**\n\n - **Surname**\n\n - **Email**\n\n - **thumbnail(url)**", tags=["User"])
async def get_user_profile(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials
    user_data = await crud.get_user_profile(user_id)

    return user_data


@user_router.get("/configuration", description="### Get full user configuration.\n\nThis endpoint returns the whole user configuration, including the user profile, the user base configuration and the user credentials.", tags=["User"])
async def get_whole_user_profile(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    user_conf = await crud.get_whole_user(user_id=user_id)

    return user_conf

@user_router.get("/login_logs", description="### Get login logs of the user", tags=["User"])
async def get_login_logs(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials
    # 'activity', 'Date/Time', 'IP Address', 'Location'

    return {"status": "under construction"}

@user_router.put("/username/{new_username}", description="### Update user username", tags=["User"])
async def update_username(new_username: str, user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    return {}

@user_router.post("/profile-configuration", description="### Update user profile configuration", tags=["User"])
async def update_user_profile_configuration(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_body: schemas.UserConfProfile):
    _, user_id = user_credentials

    # Validate UUIDset-profile-configuration
    try:
        uuid_obj = uuid.UUID(user_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Error: {user_id} is not a valid UUID4")
    
    # Update user profile
    await crud.setUserProfileBase(name=request_body.name, user_id=user_id)


@user_router.put("/change-picture/{user_id}", description="### Change user picture \n\n Change user picture", tags=["User"])
async def change_user_picture(user_id: str, file: UploadFile):
    file.filename
    file = await file.read()
    return Response(content="Under construction, not implemented", status_code=501)

@user_router.delete("/delete-account", description="### Delete all user account\n\nThis endpoint deletes all the user info and data no matter what.", tags=["User"])
async def delete_user_account(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials
    deletion = await crud.delete_user_account(user_id=user_id)

    if deletion == 200:
        session_token = encode_session_token(
            user_id=user_id,
            status="deleted",
        )
    else:
        raise HTTPException(status_code=400, detail="An error occurred while deleting the user account")

    response = JSONResponse(
        content={"redirect_url": FRONTEND_IP + "/delete_account"}
    )
    response.set_cookie(
        key="credentials",
        value=f"Bearer {session_token}",
        httponly=False,
        secure=True,
        samesite="Lax",
    )
    return response

@user_router.get("/confirm-delete", description="### Confirms deletion of an account", tags=["User"])
async def confirm_delete(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    # Decode the session token to check the status
    decoded_token = decode_session_token(user_id)
    print("Decoded token")

    if decoded_token["status"] == "deleted":
        await crud.delete_user_account(user_id=user_id)
        return Response(status_code=204)
    else:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    
@user_router.post("/starred_symbol", description="#### Add new crypto as hilighted or starred so that the user can acces to it easly", tags=["User"])
async def add_new_starred_symbol(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_boddy: schemas.CryptoSearch):
    _, user_id = user_credentials

    await crud.add_new_starred_crypto(
        user_id=user_id,
        symbol=request_boddy.symbol,
        name=request_boddy.name,
        picture_url=request_boddy.picture_url,
    )

    return Response(status_code=204)


@user_router.delete("/starred_symbol/{symbol}", description="### Remove starred symbol (saved crypto) of the user", tags=["User"])
async def remove_starred_symbol(symbol: str, user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials
    await crud.delete_starred_crypto(user_id=user_id, symbol=symbol)
    return Response(status_code=204)


@user_router.get("/symbol-detail/{symbol}", description="### See simbol  whether is **Starred** or it's **blocked** to trade\n\n This function is allowed for registered users only.\n\nFuture outputs: How many **liquidity** needs in this operation or in persentage", tags=["User"])
async def get_main_panle_crypto(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], symbol: str):
    _, user_id = user_credentials

    # Get whether is starred or not
    _is_starred_crypto = await crud.is_starred_crypto(user_id=user_id, symbol=symbol)

    # Get whether is blocked to trade or not
    # Make here the code.. 

    return {
        "is_starred": _is_starred_crypto,
        "is_blocked": False,
    }

@user_router.get("/search/cryptos", response_model=List[schemas.CryptoSearch], description="### Get last searched cryptos from a user\n\n **Return:**\n\nList[\n\n - **symbol**\n\n - **name**\n\n - **picture_url**]", tags=["User"],)
async def get_last_searched_cryptos(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)],):
    _, user_id = user_credentials

    # Get Searched Cryptos
    result = await crud.get_searched_cryptos(user_id=user_id)

    if result:
        searched_cryptos = [
            {
                "symbol": b["symbol"],
                "name": b["name"],
                "picture_url": b["picture_url"],
            }
            for b in result
        ]

        return searched_cryptos
    else:
        return []