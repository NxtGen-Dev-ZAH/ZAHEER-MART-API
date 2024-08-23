from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field


class InventoryItemBase(SQLModel):
    inventory_id: str = Field(default_factory=str, index=True, unique=True)
    product_id: str
    stock_level: int
    reserved_stock: Optional[int] = Field(default=0)
    sold_stock: Optional[int] = Field(default=0)


class InventoryItem(InventoryItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(SQLModel):
    stock_level: Optional[int] = None
    reserved_stock: Optional[int] = None
    sold_stock: Optional[int] = None
