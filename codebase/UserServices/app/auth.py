from passlib.context import CryptContext
from app import db,settings
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from app.models import UserClass
from sqlmodel import  Session, select
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")

#  Password Hashing
# poetry add "passlib[bycrypt]"

pwd_context = CryptContext(schemes="bcrypt")

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(password, hash_password):
    return pwd_context.verify(password, hash_password)


#  Check user in database



#  Genereate access_token
def generate_token(data: dict, expires_delta: timedelta|None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# verify access token/current_user
def verify_access_token(token:Annotated[str,Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

# verify refresh token
def verify_refresh_token(token:str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
