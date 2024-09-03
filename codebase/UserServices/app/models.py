from pydantic import BaseModel
from sqlmodel import SQLModel,Field
from typing import Optional
from fastapi import Form 
from typing import Annotated


class UserCreate(SQLModel):
    username: str = Field(unique=True,index = True)
    email: str = Field(unique=True,index = True)
    password: str = Field(index = True)
    shipping_address: str
    phone:int

class USERLOGIN(SQLModel):
      username: str 
      password: str

class Usertoken(SQLModel):
      username: str 
      email: str

class UserClass(UserCreate,table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True,unique=True)



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