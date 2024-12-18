# main.py
# Author: Pau Mateu
# Developer email: paumat17@gmail.com

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends, Query, UploadFile, Response
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

from src.app import schemas
from src.app.founding_rate_service.main_sercice_layer import FoundinRateService
from src.app.founding_rate_service.schedule_layer import ScheduleLayer
from src.app.founding_rate_service.bitget_layer import BitgetClient
from src.app.google_service import get_credentials_from_code, get_google_flow
from src.app.security import get_current_active_credentials_google, get_current_active_user, encode_session_token, get_current_credentials, decode_session_token
from src.app.database import crud
from src.app.database import schemas as dbschemas
# from app.utils import None
from src.config import GOOGLE_CLIENT_ID, FRONTEND_IP, PUBLIC_KEY

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
    contact={"name": "Pau Mateu", "url": "https://paumateu.com/","email": "paumat17@gmail.com"},
    servers=[{"url":"http://pauservices.top/", "description":"Spain"}, {"url":"http://localhost:8000/", "description":"localhost"}]
)

origins = [
    "http://0.0.0.0:80",
    "http://localhost:8000",
    "http://3.143.209.3/",
    "http://localhost",
    "http://pauservices.top"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    tags=["Schedule a Crypto"]
)
async def add_new_alert_if_crypto_reaches_price(request_body: schemas.CryptoAlertTask):
    # Placeholder for future implementation
    return {"status": "success", "message": "This feature is under development"}




# - - - TESTING - - -

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

#  - - - SAAS Service - - -
@app.get("/get_hight_founind_rates/{limit}", description="### Get hight funding rates\n\nGet cryptos with hight funding rates", tags=["SaaS"])
async def get_hight_founind_rates(limit):

    all_cryptos = await bitget_client.get_future_cryptos()
    fetched_crypto =  bitget_client.fetch_future_cryptos(all_cryptos)

    only_low_crypto = [{"symbol": crypto["symbol"], "fundingRate": crypto["fundingRate"]} 
                        for crypto in fetched_crypto if crypto["fundingRate"] < float(limit)]

    return only_low_crypto

@app.get("/oauth/google/login", description="Oauth 2.0 with google", tags=["Authentication"])
async def google_login():
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Ensure refresh token is always returned
    )
    return RedirectResponse(authorization_url)

@app.get("/oauth/google/callback", description="Oauth 2.0 callback", tags=["Authentication"])
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
        user_name = decoded_token.get('given_name') 
        user_surname = decoded_token.get('family_name') 
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
        # A new user has been created create the user and set default configuration
        username = f"{str(user_name).lower().replace(" ","")}{random.randint(1000, 9999)}"
        new_user_id = await crud.create_new_user(
            username=username, name=user_name, surname=user_surname,
            email=user_email, url_picture=user_picture
            )
        
        new_creds = dbschemas.CreateGoogleOAuth(
            user_id=new_user_id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry
        )
        await crud.create_google_oauth(str(user_id), new_creds)
        await crud.createDefaultConfiguration(user_id=str(new_user_id))
        type_response = "new_user"
        
    else:
        user_credentials = dbschemas.UpdateGoogleOAuth(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry
        )
        
        update_user = dbschemas.UpdateProfileUpdate(
            name=user_name,
            surname=user_surname,
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


@app.get("/historical_founding_rate/{symbol}", description="Get historical founing rate of a crypto", tags=["Metadata User"], deprecated=True)
async def get_historical_founding_rate(symbol: str):

    # historical_founding_rate = await bitget_client.get_historical_funding_rate(symbol)
    return HTMLResponse(status_code=401, content="Service not suported here")

@app.post("/search/new", description="### Add new searched crypto to historical \n\n - Needed parameter: **symbol**", tags=["Metadata User"])
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

    return Response(status_code=200)


@app.get("/search/cryptos", response_model = List[schemas.CryptoSearch], description="### Get last searched cryptos from a user\n\n **Return:**\n\nList[\n\n - **symbol**\n\n - **name**\n\n - **picture_url**]", tags=["Metadata User"])
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

@app.get("/user/profile", description="### Get perfile user data:\n\n - **Name**\n\n - **Surname**\n\n - **Email**\n\n - **thumbnail(url)**", tags=["User"])
async def get_user_profile(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request: Request):
    _, user_id = user_credentials
    user_data = await crud.get_user_profile(user_id)

    return user_data

@app.get("/user/detailed-profile", description="### Get user profile conf, everything about getting the user profile configuration", tags=["User"], )
async def get_whole_user_profile(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    user_conf = await crud.get_whole_user(user_id=user_id)

    return user_conf

@app.put("/user/username/{new_username}", description="### Update user username", tags=["User"], )
async def update_username(new_username: str, user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    return {}

@app.post("/user/profile-configuration", tags=["User"])
async def update_user_configuration(
    user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], 
    request_body: schemas.UserConfProfile, 
    request: Request
):
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
        location=request_body.location
    )

    await crud.set_user_base_config(user_config=user_config, user_id=user_id)

    if not request_body.public_email:
        await crud.delete_public_email(user_id=user_id)
    else:
        await crud.set_public_email(user_id=user_id, public_email=request_body.public_email)

    return {"success": True, "message": "User profile updated successfully"}


@app.put("/user/change-picture/{user_id}", description="### Change user picture \n\n Change user picture", tags=["User"], deprecated=True)
async def change_user_picture(user_id: str, file: UploadFile):
    file.filename
    file = await file.read()
    return Response(content="Under construction, not implemented",status_code=501)

@app.post("/user/change-email/{user_id}", description="### Endpoint to change the user email, requires oauth verification", tags=["User"], deprecated=True)
async def change_user_email(user_id: str, request_body):

    

    return Response(content="Under construction, not implemented",status_code=501)

@app.delete("/user/delete-account", description="### Delete all user account\n\nThis endpoint deletes all the user info and data no matter what.", tags=["User"])
async def delete_user_account(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    deletion = await crud.delete_user_account(user_id=user_id)

    if deletion == 200:
        session_token = encode_session_token(
            user_id=user_id,
            status="deleted"
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
        samesite='Lax'
    )
    return response



@app.get("/user/confirm-delete", description="### Confirms deletion of an account", tags=["User"])
async def confirm_delete(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    """
    Confirms the deletion status of the user account based on the session token.
    """
    _, user_id = user_credentials

    # Decode the session token to check the status
    decoded_token = decode_session_token(user_id); print("Decoded token")

    if decoded_token["status"] == "deleted":
        await crud.delete_user_account(user_id=user_id)
        return Response(status_code=204)
    else:
        raise HTTPException(status_code=403, detail="Invalid or expired token")

@app.post("/user/starred_symbol", description="#### Add new crypto as hilighted or starred so that the user can acces to it easly", tags=["User"])
async def add_new_starred_symbol(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_boddy: schemas.CryptoSearch):
    _, user_id = user_credentials

    await crud.add_new_starred_crypto(user_id=user_id, symbol=request_boddy.symbol, name=request_boddy.name, picture_url=request_boddy.picture_url)

    return Response(status_code=204)


@app.delete("/user/starred_symbol/{symbol}", description="### Remove starred symbol (saved crypto) of the user", tags=["SaaS"])
async def remove_starred_symbol(symbol: str, user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    await crud.delete_starred_crypto(user_id=user_id, symbol=symbol)

    return Response(status_code=204)

@app.get("/user/symbol-detail/{symbol}", description="### See simbol  whether is **Starred** or it's **blocked** to trade\n\n This function is allowed for registered users only.\n\nFuture outputs: How many **liquidity** needs in this operation or in persentage", tags=["SaaS"])
async def get_main_panle_crypto(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], symbol: str):
    _, user_id = user_credentials

    # Get whether is starred or not
    _is_starred_crypto = await crud.is_starred_crypto(user_id=user_id, symbol=symbol)

    # Get whether is blocked to trade or no

    return {
        "is_starred": _is_starred_crypto,
        "is_blocked": False # Crypto blocked to trade
    }




@app.get("/accounts/users", description="### Get all the asociated accounts to a user\n\nThese accounts can be both trading or sub-account", tags=["Accounts"], response_model=List[dict])
async def get_user_accounts(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    user_accounts = await crud.get_all_accounts(user_id=user_id)

    return user_accounts

@app.get("/accounts/main-account", description="### Retrieve the main trading account associated with the user", tags=["Accounts"])
async def get_main_trading_account(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]):
    _, user_id = user_credentials

    main_trading_account = await crud.get_main_trading_account(user_id=user_id)

    return {"main_trading_account": main_trading_account}

@app.post("/accounts/configuration", description="### Save accounts configuration\n\nAt this moment the only feature is to save the **main trading account**", tags=["Accounts"])
async def set_main_trading_account(user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)], request_boddy: schemas.AccountSaveConfig):
    _, user_id = user_credentials
    
    # Set main trading account
    response = await crud.set_trading_account(account_id=request_boddy.account_id, user_id=user_id)

    return Response(status_code=response)

@app.delete("/account/{account_id}", description="### Delete an asociated exchange account", tags=["Accounts"])
async def delete_account(account_id: str):
    # user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]
    # _, user_id = user_credentials

    await crud.delete_account(account_id=account_id)

    return Response(status_code=204)


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
    response_class=PlainTextResponse
)
async def get_public_key():
    pem_public_key = PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return PlainTextResponse(pem_public_key.decode('utf-8'))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
