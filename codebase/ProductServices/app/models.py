from typing import Optional
from sqlmodel import SQLModel, Field

class ProductBase(SQLModel):
    product_id: str = Field(index=True, unique=True)
    name: str
    description: str
    price: float
    is_available: bool = True
    category: Optional[str] = None

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class ProductCreate(ProductBase):
    pass


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_available: Optional[bool] = None
    category: Optional[str] = None
