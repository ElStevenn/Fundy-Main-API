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


@user_router.get("/detailed-profile", description="### Get user profile conf, everything about getting the user profile configuration", tags=["User"])
async def get_whole_user_profile(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    user_conf = await crud.get_whole_user(user_id=user_id)

    return user_conf


@user_router.put("/username/{new_username}", description="### Update user username", tags=["User"])
async def update_username(new_username: str, user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    return {}


@user_router.get("profile-configuration", description="### Get user profile configuration", tags=["User"])
async def get_users_sorted_by_joined_at(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_body: schemas.UserConfProfile):
    _, user_id = user_credentials

    # Validate UUIDset-profile-configuration
    try:
        uuid_obj = uuid.UUID(user_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Error: {user_id} is not a valid UUID4")

    # Update user profile
    await crud.setUserProfileBase(name=request_body.name, surname=request_body.surname, user_id=user_id)

    # Create UserBaseConfig instance to update configuration
    user_config = dbschemas.UserBaseConfig(
        webpage_url=request_body.webpage_url,
        bio=request_body.bio,
        main_used_exchange=request_body.main_used_exchange,
        trading_experience=request_body.trading_experience,
        location=request_body.location,
    )

    await crud.set_user_base_config(user_config=user_config, user_id=user_id)

    if not request_body.public_email:
        await crud.delete_public_email(user_id=user_id)
    else:
        await crud.set_public_email(user_id=user_id, public_email=request_body.public_email)

    return {"success": True, "message": "User profile updated successfully"}


@user_router.put("/change-picture/{user_id}", description="### Change user picture \n\n Change user picture", tags=["User"])
async def change_user_picture(user_id: str, file: UploadFile):
    file.filename
    file = await file.read()
    return Response(content="Under construction, not implemented", status_code=501)


@user_router.post("/change-email/{user_id}", description="### Endpoint to change the user email, requires oauth verification", tags=["User"])
async def change_user_email(user_id: str, request_body):
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
    
@user_router.post("/user/starred_symbol", description="#### Add new crypto as hilighted or starred so that the user can acces to it easly", tags=["User"])
async def add_new_starred_symbol(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_boddy: schemas.CryptoSearch):
    _, user_id = user_credentials

    await crud.add_new_starred_crypto(
        user_id=user_id,
        symbol=request_boddy.symbol,
        name=request_boddy.name,
        picture_url=request_boddy.picture_url,
    )

    return Response(status_code=204)


@user_router.delete("/user/starred_symbol/{symbol}", description="### Remove starred symbol (saved crypto) of the user", tags=["User"])
async def remove_starred_symbol(symbol: str, user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials
    await crud.delete_starred_crypto(user_id=user_id, symbol=symbol)
    return Response(status_code=204)


@user_router.get("/user/symbol-detail/{symbol}", description="### See simbol  whether is **Starred** or it's **blocked** to trade\n\n This function is allowed for registered users only.\n\nFuture outputs: How many **liquidity** needs in this operation or in persentage", tags=["User"])
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

