from fastapi import APIRouter, HTTPException
from typing import Annotated
from fastapi import Depends

from src.app.security import get_current_credentials
from src.app.database import crud

administrative_router = APIRouter(
    prefix="/administrative",
    tags=["Administrative"]
)

@administrative_router.get( "/joined_users", description="Get a list with recent users joined into this plataform", tags=["Administrative"])
async def get_joined_uers(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], limit: int = 100):
    _, user_id = user_credentials

    # Check if user has enought privilleges
    user = await crud.get_user_profile(user_id=user_id)

    if not user["role"] == "admin" and not user["role"] == "mod":
        return HTTPException(status_code=401, detail="You don't have enought permissions to do this")

    # Get joined users
    users = await crud.get_joined_users(limit)
    return users

@administrative_router.delete("/funding-rate/stop", description="Stop funding rate bot", tags=["Administrative"])
async def stop_funding_rate_bot():
    """Stop the funding rate bot."""

    return {"status": "Service stopped"}



