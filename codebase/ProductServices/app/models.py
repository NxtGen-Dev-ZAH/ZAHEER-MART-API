from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal


class Producttable(SQLModel, table=True):
    product_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    price: Decimal
    is_available: bool


class ProductRead(SQLModel):
    product_id: int
    name: str
    description: str
    price: Decimal
    is_available: bool


class ProductCreate(SQLModel):
    name: str
    description: str
    price: Decimal
    is_available: bool


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    is_available: Optional[bool] = None
