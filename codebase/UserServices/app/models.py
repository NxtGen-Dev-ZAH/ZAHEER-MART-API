from pydantic import BaseModel
from sqlmodel import SQLModel,Field
from typing import Optional
from fastapi import Form 
from typing import Annotated

class User(SQLModel,table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    password: str
    shipping_address: str
    phone:int

class UserCreate(SQLModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str

class RegisterUser (BaseModel):
            username: Annotated[
            str,
            Form(),
        ]
            email: Annotated[
            str,
            Form(),
        ]
            password: Annotated[
            str,
            Form(),
        ]