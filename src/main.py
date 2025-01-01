# main.py
# Author: Pau Mateu
# Developer email: paumat17@gmail.com
# v: 1.3.5

# Standard Library Imports
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone as tz
import uuid
import asyncio
import schedule
import os
import time
import threading
import pytz
import jwt
import random
import json
from typing import Annotated, List

# Third-Party Imports
from fastapi import (
    FastAPI,
    Request,
    BackgroundTasks,
    HTTPException,
    Depends,
    Query,
    UploadFile,
    Response,
    APIRouter
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    PlainTextResponse,
    HTMLResponse,
)
from cryptography.hazmat.primitives import serialization
from pytz import timezone

# Local Imports
from src.app import schemas
from src.app.founding_rate_service.main_sercice_layer import FoundinRateService
from src.app.founding_rate_service.schedule_layer import ScheduleLayer
from src.app.founding_rate_service.bitget_layer import BitgetClient
from src.app.google_service import get_credentials_from_code, get_google_flow
from src.app.security import get_current_credentials
from src.app.database import crud
from src.routes.user import user_router as user
from src.routes.auth import auth_router as auth
from src.routes.accounts import accounts_router as accounts
from src.config import PUBLIC_KEY, DOMAIN

# Initialize Scheduler and Services
async_scheduler = ScheduleLayer("Europe/Amsterdam")
founding_rate_service = FoundinRateService()
bitget_client = BitgetClient()
background_task = None

# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler
    async_scheduler.scheduler.start()
    print("Scheduler started.")

    # Initialize and start the Founding Rate Service
    if founding_rate_service.status != 'running':
        try:
            # Calculate next execution time
            next_execution_time = founding_rate_service.get_next_execution_time() - timedelta(minutes=5)
            founding_rate_service.next_execution_time = next_execution_time
            print(f"Scheduling 'innit_procces' at {next_execution_time.isoformat()} in timezone {founding_rate_service.timezone}")

            # Schedule the `innit_procces` method
            async_scheduler.schedule_process_time(next_execution_time, founding_rate_service.innit_procces)

            # Update the service status
            founding_rate_service.status = 'running'

            print("Founding Rate Service has been started successfully.")

        except Exception as e:
            print(f"Error starting Founding Rate Service: {e}")
            # Optionally, handle the exception (e.g., retry, alert, etc.)

    try:
        yield
    finally:
        # Shutdown the scheduler
        async_scheduler.scheduler.shutdown()
        print("Scheduler shut down.")

# Initialize FastAPI App
app = FastAPI(
    title="Fundy-Main-API",
    description=(
        "The **Fundy Main API** is a backend solution for managing trading accounts, user profiles, and cryptocurrency data.\n"
        "It ensures secure and efficient handling of sensitive data while offering tools for scheduling and automation.\n"
        "Designed for reliability and scalability, this API serves as the backbone for the **FUNDY** application.\n\n"

        "## **Core Capabilities**\n\n"

        "### **User Management**\n"
        "- Authentication via Google OAuth 2.0.\n"
        "- Manage user profiles and preferences.\n"
        "- Retrieve and update user-specific configurations.\n\n"

        "### **Account Management**\n"
        "- Configure trading and sub-accounts.\n"
        "- Set and retrieve the main trading account for each user.\n"
        "- Manage account permissions and associations.\n\n"

        "### **Cryptocurrency Features**\n"
        "- Retrieve cryptocurrencies with high funding rates.\n"
        "- Access historical funding rates for specific cryptocurrencies.\n"
        "- Save, highlight, and manage starred cryptocurrencies.\n\n"

        "### **Alerts and Scheduling**\n"
        "- Schedule periodic tasks and trading operations.\n"
        "- (Upcoming) Set price alerts for specific cryptocurrencies.\n\n"

        "### **Security**\n"
        "- RSA encryption for secure data handling.\n"
        "- Access the public key for encrypting sensitive information.\n\n"

        "### **Administrative Tools**\n"
        "- Monitor the status of internal services.\n"
        "- View recently joined users and system metrics.\n\n"
    ),
    lifespan=lifespan,
    version="1.3.4",
    contact={"name": "Pau Mateu", "url": "https://paumateu.com/", "email": "paumat17@gmail.com"},
    servers=[
        {"url": "http://pauservices.top/", "description": "Spain"},
        {"url": "http://localhost:8000/", "description": "localhost"},
    ],
)

router = APIRouter()
app.include_router(auth)
app.include_router(user)
app.include_router(accounts)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fundy.pauservices.top"] if DOMAIN else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# SaaS Service
@app.get(
    "/get_hight_founind_rates/{limit}",
    description="### Get hight funding rates\n\nGet cryptos with hight funding rates",
    tags=["SaaS"],
)
async def get_hight_founind_rates(limit):
    all_cryptos = await bitget_client.get_future_cryptos()
    fetched_crypto = bitget_client.fetch_future_cryptos(all_cryptos)

    only_low_crypto = [
        {"symbol": crypto["symbol"], "fundingRate": crypto["fundingRate"]}
        for crypto in fetched_crypto
        if crypto["fundingRate"] < float(limit)
    ]

    return only_low_crypto



# Metadata User
@app.get(
    "/historical_founding_rate/{symbol}",
    description="Get historical founing rate of a crypto",
    tags=["Metadata User"],
    deprecated=True,
)
async def get_historical_founding_rate(symbol: str):
    # historical_founding_rate = await bitget_client.get_historical_funding_rate(symbol)
    return HTMLResponse(status_code=401, content="Service not suported here")

@app.post(
    "/search/new",
    description="### Add new searched crypto to historical \n\n - Needed parameter: **symbol**",
    tags=["Metadata User"],
)
async def save_new_crypto(
    request_body: schemas.CryptoSearch,
    user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)],
    request: Request,
):
    _, user_id = user_credentials

    # Save searched cryptos
    result = await crud.add_new_searched_crypto(
        user_id=user_id,
        symbol=request_body.symbol,
        name=request_body.name,
        picture_url=request_body.picture_url,
    )

    return Response(status_code=200)

@app.get(
    "/search/cryptos",
    response_model=List[schemas.CryptoSearch],
    description="### Get last searched cryptos from a user\n\n **Return:**\n\nList[\n\n - **symbol**\n\n - **name**\n\n - **picture_url**]",
    tags=["Metadata User"],
)
async def get_last_searched_cryptos(
    user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)],
    request: Request,
):
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

# SaaS
@app.get(
    "/get_scheduled_cryptos",
    description="### See how many cryptos are opened or scheduled to be opened or closed (detailed data)",
    tags=["SaaS"],
)
async def get_scheduled_cryptos():
    return {"response": "under construction until the bot will work properly :)"}

# Administrative Part
@app.delete(
    "/founding_rate_service/stop",
    description="",
    tags=["Administrative Part"],
)
async def stop_founding_rate_service():
    """Stop the Founding Rate Service."""

    if founding_rate_service.status == "stopped":
        raise HTTPException(status_code=400, detail="Service is not running")

    async_scheduler.stop_all_jobs()
    founding_rate_service.status = "stopped"
    founding_rate_service.next_execution_time = None

    return {"status": "Service stopped"}

@app.get(
    "/get_joined_users/{user_id}",
    description="Get a list with recent users joined into this plataform",
    tags=["Administrative Part"],
    response_model=List[schemas.UserResponse],
)
async def get_joined_uers(
    user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)],
    limit: int,
):
    _, user_id = user_credentials

    # Check if user has enought privilleges
    user = await crud.get_user_profile(user_id=user_id)

    if not user["role"] == "admin" and not user["role"] == "mod":
        return HTTPException(status_code=401, detail="You don't have enought permissions to do this")

    # Get joined users
    users = await crud.get_joined_users(limit)
    return users

@app.get(
    "/founding_rate_service/status",
    description="",
    tags=["Administrative Part"],
)
async def see_founding_rate_service():
    """Check the status of the Founding Rate Service."""

    return {"status": founding_rate_service.status}

@app.get(
    "/get_next_execution_time",
    description="Get next execution time in iso format time",
    tags=["Administrative Part"],
)
async def next_exec_time():
    nex_exec_time = founding_rate_service.next_execution_time.isoformat()
    if not nex_exec_time:
        raise HTTPException(status_code=403, detail="The service is not running, please start the service before")

    return {"result": nex_exec_time}

@app.post(
    "/start_rest_sercies",
    description="Start Other services such as get all the cryptos an see if there are new crytpos or cryptos thare beeing deleted, among other services",
    tags=["Administrative Part"],
)
async def start_rest_services():
    return {}

@app.delete(
    "/stop_rest_services",
    description="Stop Each day tasks",
    tags=["Administrative Part"],
)
async def stop_rest_services():
    return {}

# Security
@app.get(
    "/security/get-public-key",
    description="""
    ### **GET PUBLIC KEY**

    This endpoint provides the RSA public key that can be used by clients (such as frontend applications) to **encrypt sensitive data** before sending it to the server.

    #### Encryption Details:

    - **Algorithm**: RSA (Rivest-Shamir-Adleman)
    - **Padding Scheme**: OAEP (Optimal Asymmetric Encryption Padding)
    - **Hashing Algorithm for OAEP**: SHA-256
    - **Public Key Format**: PEM (Privacy-Enhanced Mail) - Base64 encoded
    """,
    tags=["Security"],
    response_class=PlainTextResponse,
)
async def get_public_key():
    pem_public_key = PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return PlainTextResponse(pem_public_key.decode("utf-8"))

# Run Uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
