# producer: main.py
from app import kafka, models, settings
from app import product_pb2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def publish_product_created(product: models.ProductBase):
    message = kafka.product_to_proto(product)
    message.option = product_pb2.SelectOption.CREATE
    serialized_product = message.SerializeToString()
    await kafka.send_kafka_message(
        settings.KAFKA_TOPIC_PRODUCT, product.product_id, serialized_product
    )
    logger.info(f"Product created message sent for product ID: {product.product_id}")


async def publish_product_updated(product: models.ProductUpdate, product_id: str):
    product_base = models.ProductBase(
        product_id=product_id,
        name=product.name or "",
        description=product.description or "",
        price=product.price or 0.0,
        is_available=product.is_available if product.is_available is not None else True,
        category=product.category or "",
    )
    message = kafka.product_to_proto(product_base)
    message.option = product_pb2.SelectOption.UPDATE
    serialized_product = message.SerializeToString()
    await kafka.send_kafka_message(
        settings.KAFKA_TOPIC_PRODUCT, product_id, serialized_product
    )
    logger.info(
        f"===============Product updated message sent for product ID: {product_id}==========================="
    )


async def publish_product_deleted(product_id: str):
    message = product_pb2.Product(
        product_id=product_id, option=product_pb2.SelectOption.DELETE
    )
    serialized_product = message.SerializeToString()
    await kafka.send_kafka_message(
        settings.KAFKA_TOPIC_PRODUCT, product_id, serialized_product
    )
    logger.info(f"Product deleted message sent for product ID: {product_id}")


async def publish_stock_update(product_id: str, new_stock: int):
    message = product_pb2.Product(
        product_id=product_id,
        option=product_pb2.SelectOption.UPDATE,
        is_available=(new_stock > 0),
    )
    serialized_product = message.SerializeToString()
    await kafka.send_kafka_message(
        settings.KAFKA_TOPIC_STOCK_LEVEL_CHECK, product_id, serialized_product
    )
    logger.info(f"Stock update message sent for product ID: {product_id}")
