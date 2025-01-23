from fastapi import APIRouter, Depends, HTTPException, Response
from typing import Annotated
from src.app.security import get_current_credentials
from typing import List
from src.app import schemas
from src.app.database import crud



trading_bots_router = APIRouter(
    prefix="/trading-bots",
    tags=["Trading Bots"]
)


@trading_bots_router.get("/active-bots", description="### Get all the active trading bots of the user", tags=["Trading Bots"])
async def get_active_trading_bots(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials
    
    trading_bots = await crud.get_trading_bots(user_id=user_id)

    active_tradig_bots = [bot for bot in trading_bots if bot["status"] == "active"]

    return active_tradig_bots


