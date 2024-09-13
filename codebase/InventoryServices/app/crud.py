from sqlmodel import Session, select
from app.models import InventoryItemBase, InventoryItem, InventoryItemUpdate
from typing import List, Optional

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_inventory_item(
    session: Session, item: InventoryItemBase
) -> InventoryItem:
    new_item = InventoryItem(
        inventory_id=item.inventory_id,
        product_id=item.product_id,
        stock_level=item.stock_level,
        sold_stock=item.sold_stock,
        reserved_stock=item.reserved_stock,
    )
    session.add(new_item)
    session.commit()
    logger.info("Inventory data added to the  inventory database succesfully")

    session.refresh(new_item)
    return new_item


async def get_inventory_item_by_product(
    session: Session, product_id: str
) -> Optional[InventoryItem]:
    return session.exec(
        select(InventoryItem).where(InventoryItem.product_id == product_id)
    ).first()


async def get_inventory_item(
    session: Session, inventory_id: str
) -> Optional[InventoryItem]:
    return session.exec(
        select(InventoryItem).where(InventoryItem.inventory_id == inventory_id)
    ).first()


async def get_all_inventory_items(session: Session) -> List[InventoryItem]:
    return list(session.exec(select(InventoryItem)).all())


async def update_inventory_item(
    session: Session, inventory_id: str, item_data: InventoryItemUpdate
) -> Optional[InventoryItem]:
    db_item = await get_inventory_item(session, inventory_id)
    if db_item:
        logger.info(
            "----------------------------------inside the update message------------------------------------------------------"
        )
        new_product = InventoryItemUpdate(
            sold_stock=item_data.sold_stock,
            reserved_stock=item_data.reserved_stock,
            stock_level=item_data.stock_level,
        )
        logger.info(
            f"============================================{new_product}======================"
        )
        data = new_product.model_dump(exclude_unset=True)
        db_item.sqlmodel_update(data)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        logger.info("the inventory with" + inventory_id + "inventory id is updated ")

        logger.info(
            f"============================================{db_item}======================"
        )
        return db_item
    else:
        logger.error(f"Product with ID {inventory_id} not found.")


async def reduce_inventory_item(
    session: Session, product_id: str, quantity_change: int
) -> Optional[InventoryItem]:
    db_item = await get_inventory_item_by_product(session, product_id)
    if db_item and db_item.stock_level >= quantity_change:
        db_item.stock_level -= quantity_change
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
    return db_item


async def delete_inventory_item(
    session: Session, inventory_id: str
) -> Optional[InventoryItem]:
    db_item = await get_inventory_item(session, inventory_id)
    if db_item:
        session.delete(db_item)
        session.commit()
    return db_item


async def update_stock_level(
    session: Session, product_id: str, quantity_change: int
) -> Optional[InventoryItem]:
    db_item = await get_inventory_item_by_product(session, product_id)
    if db_item:
        db_item.stock_level += quantity_change
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
    return db_item
