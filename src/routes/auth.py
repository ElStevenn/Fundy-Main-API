from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from src.app.google_service import get_credentials_from_code, get_google_flow
from src.app.telegram_service import verify_telegram_oauth
from datetime import datetime, timedelta, timezone as tz
from urllib.parse import parse_qsl
import jwt, os, random, json, asyncio

from src.app.database import crud
from src.app.database import schemas as dbschemas
from src.app.security import encode_session_token

from src.config import FRONTEND_IP, DOMAIN

oauth_router = APIRouter(
    prefix="/oauth",
    tags=["Authentication"]
)

@oauth_router.get("/google/login",description="Oauth 2.0 with google",tags=["Authentication"])
async def google_login():
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(authorization_url)



@oauth_router.get("/google/callback", description="Oauth 2.0 callback", tags=["Authentication"])
async def google_callback(code: str):
    # Obtain full credentials
    try:
        credentials = get_credentials_from_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obtaining credentials: {str(e)}")

    # Decode the ID token
    id_token = credentials.id_token
    try:
        decoded_token = jwt.decode(
            id_token,
            options={"verify_signature": False},
            audience=os.getenv("GOOGLE_CLIENT_ID"),
        )

        user_email = decoded_token.get("email")
        user_name = decoded_token.get("given_name")
        user_surname = decoded_token.get("family_name")
        user_picture = decoded_token.get("picture")
        user_id = decoded_token.get("sub")

        if not user_email:
            raise HTTPException(status_code=400, detail="Email not found in token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="ID token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")

    # Check if user exists in the database
    user = await crud.check_if_user_exists(user_email)
    if not user:
        # Create new user
        username = f"{user_name.lower().replace(' ', '')}{random.randint(1000, 9999)}"
        new_user_id = await crud.create_new_user(
            username=username,
            name=user_name,
            surname=user_surname,
            email=user_email,
            url_picture=user_picture,
        )

        new_creds = dbschemas.CreateGoogleOAuth(
            user_id=new_user_id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry,
        )
        await crud.create_google_oauth(str(new_user_id), new_creds)
        await crud.createDefaultConfiguration(user_id=str(new_user_id))
        type_response = "new_user"

    else:
        # Existing user
        new_user_id = user["user_id"]

        user_credentials = dbschemas.UpdateGoogleOAuth(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry,
        )

        update_user = dbschemas.UpdateProfileUpdate(
            name=user_name,
            surname=user_surname,
            url_picture=user_picture,
        )

        update_creds = asyncio.create_task(crud.update_google_oauth(str(new_user_id), user_credentials))
        update_profile = asyncio.create_task(crud.update_profile(user_email, update_user))

        type_response = "login_user"

        await update_creds
        await update_profile

    # Generate session token
    try:
        session_token = encode_session_token(str(new_user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating session token: {str(e)}")

    # Get minimal account data
    accounts = await crud.get_accounts(user_id=new_user_id)
    account_metadata = [
        {"account_id": acc["id"], "account_name": acc["account_name"]}
        for acc in accounts
    ]

    # Cookie Parameters
    cookie_params = {
        "key": "credentials",
        "value": f"Bearer {session_token}",
        "httponly": False,
        "expires": (datetime.now(tz.utc) + timedelta(days=30)).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "secure": True if DOMAIN else False,
        "samesite": "Lax",
        "path": "/",
        "domain": ".pauservices.top" if DOMAIN else None,
    }

    account_cookie_params = {
        "key": "accounts",
        "value": json.dumps(account_metadata),
        "httponly": False,
        "expires": (datetime.now(tz.utc) + timedelta(days=30)).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "secure": True,
        "samesite": "Lax",
        "path": "/",
        "domain": ".pauservices.top" if DOMAIN else None,
    }

    # Redirect and set cookies
    if type_response == "login_user":
        response = RedirectResponse(FRONTEND_IP + "/dashboard")
    else:
        response = RedirectResponse(FRONTEND_IP + "/complete-register")

    response.set_cookie(**account_cookie_params)
    response.set_cookie(**cookie_params)

    return response


@oauth_router.get("/telegram",description="Oauth 2.0 with Telegram",tags=["Authentication"])
async def telegram_oauth(request: Request):
    query_params = dict(parse_qsl(request.url.query))

    if verify_telegram_oauth(query_params):
        user_id = query_params.get("id")
        first_name = query_params.get("first_name", "Anonymous")
        username = query_params.get("username", None)

        # Continue here

    return {"status": "under construction"}