from app import kafka, models, settings
from app import inventory_pb2
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def publish_inventory_update_stock_level(product_id: str, stock_level: int):
    message = inventory_pb2.Inventory(
        product_id=product_id,
        stock_level=stock_level,
        option=inventory_pb2.SelectOption.ADD,
    )
    serialized_message = message.SerializeToString()
    await kafka.send_kafka_message(settings.KAFKA_TOPIC_INVENTORY, serialized_message)
    logger.info(
        f"Inventory update stock level message sent for product ID: {product_id}"
    )


async def publish_inventory_create(inventory_id, item: models.InventoryItemCreate):
    message = inventory_pb2.Inventory(
        inventory_id=inventory_id,
        stock_level=item.stock_level,
        product_id=item.product_id,
        reserved_stock=item.reserved_stock,
        sold_stock=item.sold_stock,
        option=inventory_pb2.SelectOption.CREATE,
    )
    serialized_message = message.SerializeToString()
    await kafka.send_kafka_message(settings.KAFKA_TOPIC_INVENTORY, serialized_message)
    logger.info(f"Inventory create message sent for product ID: {inventory_id}")


async def publish_inventory_update(inventory_id: str, item: models.InventoryItemUpdate):
    message = inventory_pb2.Inventory(
        inventory_id=inventory_id,
        stock_level=item.stock_level,
        reserved_stock=item.reserved_stock,
        sold_stock=item.sold_stock,
        option=inventory_pb2.SelectOption.UPDATE,
    )
    serialized_message = message.SerializeToString()
    await kafka.send_kafka_message(settings.KAFKA_TOPIC_INVENTORY, serialized_message)
    logger.info(f"Inventory update message sent for product ID: {inventory_id}")


async def publish_inventory_reduce(product_id: str, stock_level: int):
    message = inventory_pb2.Inventory(
        product_id=product_id,
        stock_level=stock_level,
        option=inventory_pb2.SelectOption.REDUCE,
    )
    serialized_message = message.SerializeToString()
    await kafka.send_kafka_message(settings.KAFKA_TOPIC_INVENTORY, serialized_message)
    logger.info(f"Inventory reduce message sent for product ID: {product_id}")


async def publish_inventory_check(product_id: str):
    message = inventory_pb2.Inventory(
        product_id=product_id, option=inventory_pb2.SelectOption.CHECK
    )
    serialized_message = message.SerializeToString()
    await kafka.send_kafka_message(settings.KAFKA_TOPIC_INVENTORY, serialized_message)
    logger.info(f"Inventory check message sent for product ID: {product_id}")


async def publish_product_deleted(inventory_id: str):
    message = inventory_pb2.Inventory(
        inventory_id=inventory_id, option=inventory_pb2.SelectOption.DELETE
    )
    serialized_product = message.SerializeToString()
    await kafka.send_kafka_message(settings.KAFKA_TOPIC_INVENTORY, serialized_product)
    logger.info(f"Product deleted message sent for product ID: {inventory_id}")
