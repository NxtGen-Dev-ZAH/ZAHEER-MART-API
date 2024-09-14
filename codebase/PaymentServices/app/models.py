# models.py
from pydantic import BaseModel
from typing import Optional
from pydantic import BaseModel
from fastapi import Form
from sqlmodel import SQLModel, Field

class CheckoutRequest(BaseModel):
    amount: int  # Amount in cents
    currency: str  # Currency code, e.g., 'usd'

class PAYMENTmodel(SQLModel):
    order_id: str = Field(index=True)
    user_id: str = Field(index=True)

class Payment(PAYMENTmodel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    payment_status: str = Field(default="Pending", index=True)
    payment_id: str = Field(index=True, unique=True)

class PaymentRequest(SQLModel):
    amount: int
    card_number: int
    exp_month: int
    exp_year: int
    cvc: int
    order_id: str

class User(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, unique=True)
    username: str = Field(index=True)
    email: str = Field(index=True)
    password: str = Field(index=True)