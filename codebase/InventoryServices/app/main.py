from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session
from app import models, crud, kafka, settings
from app.producer import producer
from app.consumer import main
from .db import get_session, create_db_and_tables
import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Annotated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    await kafka.create_topic()
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(main.start_consuming_product())
    task2 = loop.create_task(main.start_consuming())
    task3 = loop.create_task(main.start_consuming_inventory_check())
    try:
        yield
    finally:
        for task in [task1, task2, task3]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"Hello": "Welcome to Inventory Service ."}


@app.get("/inventory/{inventory_item}", response_model=models.InventoryItem)
async def see_inventory_item(
    inventory_item: str, session: Annotated[Session, Depends(get_session)]
):
    # , session: Annotated[Session, Depends(get_session)
    # inventoryitem = await producer.publish_inventory_check(inventory_item)
    inventoryitem = await crud.get_inventory_item(session, inventory_item)
    if inventoryitem is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return inventoryitem


@app.get("/inventory/", response_model=list[models.InventoryItemBase])
async def get_all_inventory_items(session: Annotated[Session, Depends(get_session)]):
    items = await crud.get_all_inventory_items(session)
    return items


@app.post("/inventory/create/")
async def create_inventory_item(item: models.InventoryItemCreate):
    await producer.publish_inventory_create(item.inventory_id, item)
    return {
        "message": "Inventory creation request sent. YOU IDIOT",
        "inventory_id": item.inventory_id,
    }

    # async for message in kafka.consume_messages(
    #     settings.KAFKA_TOPIC_INVENTORY,
    #     settings.KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY,
    # ):
    #     if message.error_message or message.http_status_code:
    #         raise HTTPException(
    #             status_code=message.http_status_code, detail=message.error_message
    #         )
    #     else:
    #         product_return_from_db = models.InventoryItem(
    #             id=message.id,
    #             inventory_id=message.inventory_id,
    #             product_id=message.product_id,
    #             reserved_stock=message.reserved_stock,
    #             sold_stock=message.sold_stock,
    #             stock_level=message.stock_level,
    #         )
    #     return product_return_from_db


@app.put("/inventory/{inventory_id}/add", response_model=models.InventoryItem)
async def update_inventory_item(
    inventory_id: str,
    item: models.InventoryItemUpdate,
    session: Annotated[Session, Depends(get_session)],
):
    # if db_item is None:
    # raise HTTPException(status_code=404, detail="Inventory item not found")
    await producer.publish_inventory_update(inventory_id, item)
    inventoryitem = await crud.get_inventory_item(session, inventory_id)
    if inventoryitem is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    return inventoryitem


@app.delete("/inventory/{inventory_id}")
async def delete_inventory_item(inventory_id: str):
    await producer.publish_product_deleted(inventory_id)
    return {"inventory of inventory_id " + inventory_id + "is deleted successfully"}


@app.put("/inventory/{product_id}/update_stock")
async def update_stock_level(
    product_id: str,
    quantity_change: int,
):
    await producer.publish_inventory_update_stock_level(product_id, quantity_change)
    return {"message": "Stock updated successfully"}


@app.put("/inventory/{product_id}/reduce", response_model=models.InventoryItemBase)
async def reduce_stock_level(product_id: str, quantity_change: int):
    await producer.publish_inventory_reduce(product_id, quantity_change)
    return {"message": "Stock reduced successfully"}
