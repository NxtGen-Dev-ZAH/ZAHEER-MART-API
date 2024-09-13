# consumer: main.py

from sqlmodel import Session, select
from app import kafka, settings, crud, db, product_pb2
import logging
from app.models import Product, ProductUpdate, ProductBase
import asyncio
from app.kafka import retry_async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_create_product(product_data: ProductBase):
    with Session(db.engine) as session:
        created_product = await crud.create_product_crud(session, product_data)
        return created_product


async def handle_update_product(product_data: ProductUpdate, product_id: str):
    with Session(db.engine) as session:
        updated_product = await crud.update_product(session, product_id, product_data)
        logger.info(
            f"======= updated yahoo in consumer ==== {updated_product}===================="
        )
        return updated_product


async def handle_delete_product(product_id: str):
    with Session(db.engine) as session:
        deleted_product = await crud.delete_product(session, product_id)
        return deleted_product


async def process_message(product: product_pb2.Product):
    try:
        # Assuming 'products' is the repeated field in ProductList
        if product.option == product_pb2.SelectOption.CREATE:
            await handle_create_product(product)
        elif product.option == product_pb2.SelectOption.UPDATE:
            logger.info("========sending to the message for update ============")
            await handle_update_product(product, product.product_id)
            logger.info(f"Product with ID {product.product_id} updated successfully.")
        elif product.option == product_pb2.SelectOption.DELETE:
            await handle_delete_product(product.product_id)
        else:
            logger.warning(f"Unknown option: {product.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def process_message_stock(new_msg: product_pb2.Inventory):
    with Session(db.engine) as session:
        product = await crud.get_product(session, new_msg.product_id)
        if product is not None:
            if new_msg.stock_level <= 0:
                product.is_available = False
            elif new_msg.stock_level > 0:
                product.is_available = True
                session.add(product)
                session.commit()


async def start_consuming():
    try:
        consumer = kafka.consume_messages(
            settings.KAFKA_TOPIC_PRODUCT, settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT
        )
        async for message in consumer:
            await process_message(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


async def start_consuming_stock():
    try:
        consumer = kafka.consume_messages_stock(
            settings.KAFKA_TOPIC_STOCK_LEVEL_CHECK,
            settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT,
        )
        async for message in consumer:
            await process_message_stock(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


# if __name__ == "__main__":
#     asyncio.run(start_consuming())
#     asyncio.run(start_consuming_stock())
