from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from cryptography.fernet import Fernet
from typing import Annotated
from uuid import UUID
import jwt

from app.database.crud import get_google_credentials
from config import JWT_SECRET_KEY, PRIVATE_KEY, PUBLIC_KEY



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
            status_code=401,
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
 
    credentials = await get_google_credentials(user_id)
    return credentials, user_id


async def get_current_active_credentials_google(
        current_user_credentials: Annotated[tuple[dict, str], Depends(get_current_credentials)]
    ):
    credentials, user_id = current_user_credentials  
    return user_id, credentials


"""
 - - -  ENCRYPTION - - -
"""

"""
cipher_suite = Fernet(PRIVATE_KEY)

def encrypt_data(plain_text):
    encrypted_data = cipher_suite.encrypt(plain_text.encode('utf-8'))
    return encrypted_data

def decrypt_data(encrypted_data):
    decrypted_data = cipher_suite.decrypt(encrypted_data).decode('utf-8')
    return decrypted_data


if __name__ == "__main__":
    # Example usage
    text = "my-text123"
"""
