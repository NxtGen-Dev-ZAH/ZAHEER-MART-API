# main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session
from app import models, crud, kafka
from app.producer import producer
from app.consumer.main import start_consuming, start_consuming_stock


# from app.consumer.main import consume_message_for_stock_level_update
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
    task = asyncio.create_task(start_consuming())
    stock_task = asyncio.create_task(start_consuming_stock())
    try:
        yield
    finally:
        for consumer in [task, stock_task]:
            consumer.cancel()
            try:
                await consumer
            except asyncio.CancelledError:
                pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def main():
    return "welcome to Product services "   


#  The Order Service will request product details from the Product Service during order creation.
#  This communication will be synchronous using REST API (FastAPI).
@app.get("/products/{product_id}/details", response_model=models.Product)
async def get_product_details(
    product_id: str, session: Annotated[Session, Depends(get_session)]
):
    db_product = await crud.get_product(session, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.get("/products/", response_model=list[models.ProductBase])
async def read_products(session: Annotated[Session, Depends(get_session)]):
    products = await crud.get_all_products(session)
    return products


@app.post("/products/", response_model=models.ProductBase)
async def create_product(product: models.ProductBase):
    await producer.publish_product_created(product)
    return product


@app.patch("/products/{product_id}")
async def update_product(
    product_id: str,
    product: models.ProductUpdate,
):
    await producer.publish_product_updated(product, product_id)
    return {"detail": f"Update request for product ID {product_id} has been sent."}


@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    product = await producer.publish_product_deleted(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return f"Product with id {product_id}  is deleted : {product}"


# @app.post("/products/{product_id}/update_stock")
# async def update_product_stock(
#     product_id: str, new_stock: int, session: Annotated[Session, Depends(get_session)]
# ):
#     db_product = await crud.update_product_stock(session, product_id, new_stock)
#     if db_product is None:
#         raise HTTPException(status_code=404, detail="Product not found")
#     await producer.publish_stock_update(product_id, new_stock)
#     return {"message": "Stock updated successfully"}

# @app.post("/products/{product_id}/check_stock")
# async def check_stock(product_id: str, quantity: int, session: Annotated[Session, Depends(get_session)]):
#     db_product = await crud.get_product(session, product_id)
#     if db_product is None:
#         raise HTTPException(status_code=404, detail="Product not found")

#     # Assuming we have a stock field in the Product model
#     if db_product.stock >= quantity:
#         return {"available": True, "message": "Sufficient stock available"}
#     else:
#         return {"available": False, "message": "Insufficient stock"}
