# main.py
# Author: Pau Mateu
# Developer email: paumat17@gmail.com

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from typing import Annotated, List
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.responses import RedirectResponse
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta
from pytz import timezone
import uuid, asyncio, schedule, os, time, threading, pytz, jwt, random


from app import redis_service, schemas
from app.founding_rate_service.main_sercice_layer import FoundinRateService
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.founding_rate_service.schedule_layer import ScheduleLayer
from app.founding_rate_service.bitget_layer import BitgetClient
from app.google_service import get_credentials_from_code, get_google_flow
from app.security import get_current_active_credentials_google, get_current_active_user, encode_session_token, get_current_credentials
from app.database import crud
from app.database import schemas as dbschemas
from config import GOOGLE_CLIENT_ID, FRONTEND_IP, PUBLIC_KEY

async_scheduler = ScheduleLayer("Europe/Amsterdam")


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



app = FastAPI(
    title="Leverage's Main API",
    description=(
        "This API provides services related to cryptocurrency funding rates and user management. "
        "It integrates with third-party platforms like Google for OAuth2 authentication and allows for tracking cryptocurrency funding rates.\n\n"
        
        "### Authentication:\n"
        "Most endpoints require authentication. Please include your API key in the `Authorization` header "
        "as a Bearer token when making requests. For example:\n"
        "```\n"
        "Authorization: Bearer YOUR_API_KEY\n"
        "```\n"
        
        "### Key Features:\n"
        "- **Cryptocurrency Funding Rates**: Retrieve and analyze historical and real-time funding rates for various cryptocurrencies.\n"
        "- **User Management**: Authenticate users via Google OAuth2 and manage user profiles.\n"
        "- **Administrative Control**: Start and stop services related to funding rates and get information about joined users.\n\n"
        
        "### Summary:\n"
        "Leverage's Main API is a powerful tool for managing cryptocurrency funding rates, user authentication, and profile management, "
        "with integrations for real-time data and third-party authentication services."
    ),
    lifespan=lifespan,
    version="1.3.4",
    servers=[{"url":"http://localhost:8000/", "description":"EU"}] # {"url":"http://18.101.108.204/", "description":"USA"},
)

origins = [
    "http://0.0.0.0:80",
    "http://localhost:8000",
    "http://3.143.209.3/",
    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_service_ = redis_service.RedisService()
founding_rate_service = FoundinRateService()
bitget_client = BitgetClient()
background_task = None 


def run_scheduler(loop):
    asyncio.set_event_loop(loop)
    while True:
        schedule.run_pending()
        time.sleep(1)

# CRYPTO / INDEX reach a certain price
@app.put(
    "/add_new_alert", 
    description=(
        "Add a new alert for when a cryptocurrency reaches a specific price.\n\n"
        "This endpoint is intended to allow users to set up alerts for when a specified cryptocurrency reaches a target price. "
        "However, this feature is currently under development and is not available at this time.\n\n"
        
        "### Current Status:\n"
        "This feature is under development and will be available in a future release."
    ), 
    tags=["Schedule By Crypto"]
)
async def add_new_alert_if_crypto_reaches_price(request_body: schemas.CryptoAlertTask):
    # Placeholder for future implementation
    return {"status": "success", "message": "This feature is under development"}




# PART 3 | FOUNDING RATE SERVICE

def next_execution_time_test(minutes = 5) -> datetime:
    today = datetime.now(timezone('Europe/Amsterdam'))
    next_time = today + timedelta(minutes=minutes)
    return next_time


@app.get("/test_schedule", tags=['Testing'])
async def test_dirty_schedule(background_tasks: BackgroundTasks):
    today = datetime.now(timezone('Europe/Amsterdam'))
    nex_time = today + timedelta(minutes=2)

    loop = asyncio.get_event_loop()
    loop.call_later(nex_time)

    return {"message": "in theory the function has been scheduled, look at the terminal :O"}

@app.get("/get_next_execution_time", tags=['Testing'])
async def next_execution_time():
    return {"next_execution_time": founding_rate_service.next_execution_time}

# SAAS Service
@app.get("/get_hight_founind_rates/{limit}", description="", tags=["SaaS"])
async def get_hight_founind_rates(limit):

    all_cryptos = await bitget_client.get_future_cryptos()
    fetched_crypto =  bitget_client.fetch_future_cryptos(all_cryptos)

    only_low_crypto = [{"symbol": crypto["symbol"], "fundingRate": crypto["fundingRate"]} 
                        for crypto in fetched_crypto if crypto["fundingRate"] < float(limit)]

    return only_low_crypto

@app.get("/google/login", description="Oauth 2.0 with google", tags=["SaaS"])
async def google_login():
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Ensure refresh token is always returned
    )
    return RedirectResponse(authorization_url)

@app.get("/google/callback", description="Oauth 2.0 callback", tags=["SaaS"])
async def google_callback(code: str):
    # Get full credentials
    try:
        credentials = get_credentials_from_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obtaining credentials: {str(e)}")
    
    # Get Name, Surname, picutre, username, user id....
    id_token = credentials.id_token
    try:
        decoded_token = jwt.decode(
            id_token,
            options={"verify_signature": False},
            audience=GOOGLE_CLIENT_ID
        )
        
        user_email = decoded_token.get('email')
        user_name = decoded_token.get('name') 
        user_given_name = decoded_token.get('given_name') 
        user_family_name = decoded_token.get('family_name') 
        user_picture = decoded_token.get('picture') 
        user_id = decoded_token.get('sub')  
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Email not found in token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="ID token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")

    # Create / Update credentials and permissions
    user = await crud.check_if_user_exists(user_email)
    if not user: 
        # Create username (make it up)
        username = f"{str(user_given_name).lower().replace(" ","")}{random.randint(1000, 9999)}"
        new_user_id = await crud.create_new_user(
            username=username, name=user_name, surname=user_family_name,
            email=user_email, url_picture=user_picture
            )
        
        new_creds = dbschemas.CreateGoogleOAuth(
            user_id=new_user_id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry
        )
        await crud.create_google_oauth(str(user_id), new_creds)
        type_response = "new_user"
        
    else:
        user_credentials = dbschemas.UpdateGoogleOAuth(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry
        )
        update_user = dbschemas.UpdateProfileUpdate(
            name=user_name,
            surname=user_family_name,
            url_picture=user_picture
        )

        update_creds = asyncio.create_task(crud.update_google_oauth(str(user_id), user_credentials))
        update_profile = asyncio.create_task(crud.update_profile(user_email, update_user))

        type_response = "login_user"
        new_user_id = user['user_id']

        await update_creds
        await update_profile

    # Generate Beaber Token
    try:
        session_token = encode_session_token(
            str(new_user_id)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating session token: {str(e)}")

    # Redirect to the needed page whether register or login and set the needed cookies
    if type_response == "login_user":
        response = RedirectResponse(f"{FRONTEND_IP}/dashboard")
        response.set_cookie(
            key="credentials",
            value=f"Bearer {session_token}",
            httponly=False,
            secure=True,   
            samesite='Lax'
        )
        return response


    elif type_response == "new_user":
        response = RedirectResponse(f"{FRONTEND_IP}/complete-register")
        response.set_cookie("credentials", value=f"Bearer {session_token}")
        return response


@app.get("/get_historical_founding_rate/{symbol}", description="Get historical founing rate of a crypto", tags=["SaaS"])
async def get_historical_founding_rate(symbol: str):
    historical_founding_rate = await bitget_client.get_historical_funding_rate(symbol)
    return historical_founding_rate

@app.post("/new_searched_crypto", description="### Add new searched crypto\n\n - Needed parameter: **symbol**", tags=["SaaS"])
async def save_new_crypto(
    request_body: schemas.CryptoSearch,
    user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)],
    request: Request
):
    _, user_id = user_credentials

    # Save searched cryptos
    result = await crud.add_new_searched_crypto(
        user_id=user_id,
        symbol=request_body.symbol,
        name=request_body.name,
        picture_url=request_body.picture_url
    )

    return {"response": "crypto has been saved successfully"}


@app.get("/get_last_searched_cryptos", response_model = List[schemas.CryptoSearch], description="### Get last searched cryptos from a user\n\n **Return:**\n\nList[\n\n - **symbol**\n\n - **name**\n\n - **picture_url**]", tags=["SaaS"])
async def get_last_searched_cryptos(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request: Request):
    _, user_id = user_credentials

    # Get Searched Cryptos
    result = await crud.get_searched_cryptos(user_id=user_id)

    if result:
        searched_cryptos = [
            {
                "symbol": b["symbol"],
                "name": b["name"],
                "picture_url": b["picture_url"]
            }
            for b in result
        ]

        return searched_cryptos
    else:
        return []

@app.get("/get_random_faq", description="Get random phrase to put it in the FAQ part", tags=["SaaS"])
async def get_radom_faq():
    return {"response": "under construction"}

@app.get("/get_user_profile", description="### Get perfile user data:\n\n - **Name**\n\n - **Surname**\n\n - **Email**\n\n - **thumbnail(url)**", tags=["SaaS"])
async def get_user_profile(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request: Request):
    _, user_id = user_credentials
    user_data = await crud.get_user_profile(user_id)

    return user_data

@app.post("/set_user_configuration", description="### Update user configuration data:\n\n - **minimum_founding_rate**\n\n - **User Exchange**", tags=["SaaS"])
async def update_user_configuration(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_body: schemas.UpdateUserConf):
    _, user_id = user_credentials

    return {}

@app.post("/set_userkeys", description="### Set user keys to use the exchange \n\n**Required data:**\n\n - Encrypted Apikey\n\n - Encrypted Secret Key\n\n - ", tags=["SaaS"])
async def set_user_credentials(request_body: schemas.UserCredentials, user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    response = await crud.set_new_user_credentials(user_id, encrypted_apikey=request_body.encrypted_apikey, encrypted_secret_key=request_body.encrypted_secret_key, encrypted_passphrase=request_body.encrypted_passphrase)

    return response

@app.post("/create_new_account", description="### Create a new account for the user\n\n**Required data:**\n\n - Account Type\n\n - Email\n\n", tags=["SaaS"])
async def create_new_account(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_boddy: schemas.UserAccount):
    _, user_id = user_credentials

    response = await crud.create_new_account(user_id=user_id, email=request_boddy.email, type=request_boddy.type)

    return response

@app.get("/get_user_accounts",description="### Get list of accounts from a user\n\nIf user doesn't have any account, it'll return a void array ", tags=["SaaS"], response_model=List[dict])
async def get_user_accounts(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    user_accounts = await crud.get_list_id_accounts(user_id=user_id)

    return user_accounts

@app.get("/get_scheduled_cryptos", description="### See how many cryptos are opened or scheduled to be opened or closed (detailed data)", tags=["SaaS"])
async def get_scheduled_cryptos():
    return {"response": "under construction until the bot will work properly :)"}


"""
 - - - ADMINISTRATIVE PART - - - 
"""

@app.delete("/founding_rate_service/stop", description="", tags=['Administrative Part'])
async def stop_founding_rate_service():

    """Stop the Founding Rate Service."""

    if founding_rate_service.status == "stopped":
        raise HTTPException(status_code=400, detail="Service is not running")

    async_scheduler.stop_all_jobs()
    founding_rate_service.status = "stopped"
    founding_rate_service.next_execution_time = None

    return {"status": "Service stopped"}

@app.get("/get_joined_users/{user_id}", description="Get a list with recent users joined into this plataform", tags=['Administrative Part'], response_model=List[schemas.UserResponse]) # 
async def get_joined_uers(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], limit: int):
    _, user_id = user_credentials

    # Check if user has enought privilleges
    user = await crud.get_user_profile(user_id=user_id)

    if not user["role"] == "admin" and not user["role"] == "mod":
        return HTTPException(status_code=401, detail="You don't have enought permissions to do this")

    # Get joined users
    users = await crud.get_joined_users(limit)
    return users

@app.get("/founding_rate_service/status", description="", tags=['Administrative Part'])
async def see_founding_rate_service():
    """Check the status of the Founding Rate Service."""

    return {"status": founding_rate_service.status}

@app.get("/get_next_execution_time", description="Get next execution time in iso format time", tags=['Administrative Part'])
async def next_exec_time():
    nex_exec_time = founding_rate_service.next_execution_time.isoformat()
    if not nex_exec_time:
        raise HTTPException(status_code=403, detail="The service is not running, please start the service before")
    
    return {"result": nex_exec_time}

@app.post("/start_rest_sercies", description="Start Other services such as get all the cryptos an see if there are new crytpos or cryptos thare beeing deleted, among other services", tags=['Administrative Part'])
async def start_rest_services():
    return {}

@app.delete("/stop_rest_services", description="Stop Each day tasks",tags=['Administrative Part'])
async def stop_rest_services():
    return {}

# Security
@app.get("/security/get-public-key", description="### **GET PUBIC KEY**\n\n - Here is where you can get a public key to encrypt the **sensitive data**", tags=["Security"], response_class=PlainTextResponse)
async def get_public_key():
    # user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]
    # _, user_id = user_credentials

    pem_public_key = PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return PlainTextResponse(pem_public_key.decode('utf-8'))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
