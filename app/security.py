from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated
from uuid import UUID
import jwt

from app.database.crud import get_google_credentials
from config import JWT_SECRET_KEY



ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def encode_session_token(user_id: str):
    expiration = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,  
        "exp": expiration 
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_session_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail="Session has expired",
            headers={"WWW-Authenticate": "Bearer"}
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=400,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}  
        )
    
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user_id = decode_session_token(token)
    return UUID(user_id)

async def get_current_active_user(
    current_user_id: Annotated[UUID, Depends(get_current_user)],
):
    return current_user_id

async def get_current_credentials(token: Annotated[str, Depends(oauth2_scheme)]):
    user_id = decode_session_token(token)
 
    credentials = get_google_credentials(user_id)
    return credentials


async def get_current_active_credentials_google(
        current_user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]
    ):
    credentials, service = current_user_credentials  
    return credentials, service