#models.py
from typing import Optional
from sqlmodel import SQLModel, Field

class OrdersBase(SQLModel):
    order_id: str = Field(default_factory=str,unique=True, index=True)
    product_id:str  = Field(index=True)
    user_id:str  = Field(index=True)
    quantity: int = Field(index=True)
    shipping_address: str = Field(index=True)
    customer_notes: str = Field(index=True)
    order_status: str = Field(default="In_progress", index=True)
    payment_status: str = Field(default="Pending", index=True)

class Orders(OrdersBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class OrdersCreate(SQLModel):
    order_id: str = Field(default_factory=str,unique=True, index=True)
    product_id: str
    user_id: str
    quantity: int
    shipping_address: str
    customer_notes: str

class OrdersUpdate(SQLModel):
    quantity: Optional[int] = None
    shipping_address: Optional[str] = None
    customer_notes: Optional[str] = None
    order_status: Optional[str] = None
    payment_status: Optional[str] = None

class UserBase(SQLModel):
    user_id: str = Field(default_factory=str, index=True)
    username: str = Field(index=True)
    email: str = Field(index=True)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    password: str = Field(index=True)

class UserCreate(UserBase):
    password: str

class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
