from sqlmodel import Session, select
from app.models import InventoryItemBase, InventoryItemTable
from typing import List, Optional

async def create_inventory_item(session: Session, item: InventoryItemBase) -> InventoryItemTable:
    new_item = InventoryItemTable(
        product_id=item.product_id,
        quantity=item.quantity,
                )
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item

async def get_inventory_item(session: Session, product_id: str) -> Optional[InventoryItemTable]:
    return session.exec(select(InventoryItemTable).where(InventoryItemTable.product_id == product_id)).first()

async def get_all_inventory_items(session: Session) -> List[InventoryItemTable]:
    return list(session.exec(select(InventoryItemTable)).all())

async def update_inventory_item(session: Session, product_id: str, item_data: dict) -> Optional[InventoryItemTable]:
    db_item = await get_inventory_item(session, product_id)
    if db_item:
        for key, value in item_data.items():
            setattr(db_item, key, value)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
    return db_item

async def delete_inventory_item(session: Session, product_id: str) -> Optional[InventoryItemTable]:
    db_item = await get_inventory_item(session, product_id)
    if db_item:
        session.delete(db_item)
        session.commit()
    return db_item

async def update_stock_level(session: Session, product_id: str, quantity_change: int) -> Optional[InventoryItemTable]:
    db_item = await get_inventory_item(session, product_id)
    if db_item:
        db_item.quantity += quantity_change
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
    return db_item