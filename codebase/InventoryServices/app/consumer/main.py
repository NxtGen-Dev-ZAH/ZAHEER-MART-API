from sqlmodel import Session
from app import kafka, settings, crud
from app import db
from app import inventory_pb2
import logging
from app.models import (
    InventoryItemBase,
    InventoryItem,
    InventoryItemUpdate,
    InventoryItemCreate,
)
import asyncio


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_inventory_check_by_product(product_id: str):
    with Session(db.engine) as session:
        item = await crud.get_inventory_item_by_product(session, product_id)
        return item


async def handle_inventory_check(inventory_id: str):
    with Session(db.engine) as session:
        item = await crud.get_inventory_item(session, inventory_id)
        return item


async def handle_inventory_stock_level_update(product_id: str, quantity_change: int):
    with Session(db.engine) as session:
        updated_item = await crud.update_stock_level(
            session, product_id, quantity_change
        )
        return updated_item


async def handle_inventory_update( inventory: InventoryItemUpdate ,inventory_id: str):
    with Session(db.engine) as session:
        updated_item = await crud.update_inventory_item(session, inventory_id, inventory)
        logger.info(
            f"======= updated yahoo in consumer ==={updated_item}===================="
        )
        return updated_item


async def handle_inventory_create(inventory: InventoryItemCreate):
    with Session(db.engine) as session:
        new_item = await crud.create_inventory_item(session, inventory)
        logger.info(f"New inventory item created: {new_item}")
        return new_item


async def handle_inventory_reduce(product_id: str, quantity_change: int):
    with Session(db.engine) as session:
        updated_item = await crud.reduce_inventory_item(
            session, product_id, quantity_change
        )
        return updated_item


async def handle_delete_inventory(inventory_id: str):
    with Session(db.engine) as session:
        deleted_product = await crud.delete_inventory_item(session, inventory_id)
        return deleted_product


async def process_message(inventory: inventory_pb2.Inventory):
    try:
        if inventory.option == inventory_pb2.SelectOption.CHECK:
            await handle_inventory_check(inventory.inventory_id)
        elif inventory.option == inventory_pb2.SelectOption.CREATE:
            await handle_inventory_create(inventory)
        elif inventory.option == inventory_pb2.SelectOption.CHECK_BY_PRODUCT:
            await handle_inventory_check_by_product(inventory.product_id)
        elif inventory.option == inventory_pb2.SelectOption.UPDATE:
            await handle_inventory_update(inventory,inventory.inventory_id)
        elif inventory.option == inventory_pb2.SelectOption.ADD:
            await handle_inventory_stock_level_update(
                inventory.product_id, inventory.stock_level
            )
        elif inventory.option == inventory_pb2.SelectOption.REDUCE:
            await handle_inventory_reduce(inventory.product_id, inventory.stock_level)
        elif inventory.option == inventory_pb2.SelectOption.DELETE:
            await handle_delete_inventory(inventory.inventory_id)

        # elif message.option == inventory_pb2.SelectOption.DELETE:
        #     await handle_delete_inventory(message.inventory_id)

        else:
            logger.warning(f"Unknown option: {inventory.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def process_message_inventory_check(new_msg: inventory_pb2.Order):
    with Session(db.engine) as session:
        try:

            if new_msg.option == inventory_pb2.SelectOption.PAYMENT_DONE:
                inventory = await crud.get_inventory_item_by_product(
                    session, new_msg.product_id
                )
                logger.info(
                    f"new_msg received at the consumer on the consumer side of inventory: {inventory}"
                )
                if inventory is not None:
                    await handle_inventory_reduce(
                        inventory.product_id, new_msg.quantity
                    )
            else:
                logger.warning(
                    f"No inventory item found for product ID: {new_msg.product_id}"
                )
        except Exception as e:
            logger.error(f"Error processing message: {e}")


async def process_message_product(product: inventory_pb2.Product):
    with Session(db.engine) as session:
        try:
            if product.option == inventory_pb2.SelectOption.CREATE:
                # Create an inventory item for the newly created product
                inventory_item = InventoryItemBase(
                    product_id=product.product_id,
                    stock_level=0,
                    reserved_stock=0,
                    sold_stock=0,
                )
                session.add(inventory_item)
                session.commit()
                session.refresh(inventory_item)
                logger.info(
                    f"Created inventory item for product ID: {product.product_id}"
                )

            elif product.option == inventory_pb2.SelectOption.DELETE:
                # Delete the inventory item for the deleted product
                inventory_item = handle_inventory_check_by_product(product.product_id)

                if inventory_item:
                    session.delete(inventory_item)
                    session.commit()

                    logger.info(
                        f"Deleted inventory item for product ID: {product.product_id}"
                    )
                else:
                    logger.warning(
                        f"No inventory item found for product ID: {product.product_id}"
                    )

            else:
                logger.warning(f"Unknown option: {product.option}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")


async def start_consuming():
    try:
        async for message in kafka.consume_messages(
            settings.KAFKA_TOPIC_INVENTORY,
            settings.KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY,
        ):
            await process_message(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


async def start_consuming_product():
    try:
        async for message in kafka.consume_messages_product(
            settings.KAFKA_TOPIC_GET_PRODUCT,
            settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT,
        ):
            await process_message_product(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


async def start_consuming_inventory_check():
    try:
        async for message in kafka.consume_messages_inventory_check(
            settings.KAFKA_TOPIC_INVENTORY_CHECK_REQUEST,
            settings.KAFKA_CONSUMER_GROUP_ID_FOR_INVENTORY_CHECK,
        ):
            await process_message_inventory_check(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


if __name__ == "__main__":
    asyncio.run(start_consuming())
