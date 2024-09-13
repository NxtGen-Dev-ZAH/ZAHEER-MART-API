# kafka.py
import asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.admin import NewTopic
from . import settings, models
from app import product_pb2
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_topic():
    admin_client = AIOKafkaAdminClient(bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}")
    await retry_async(admin_client.start)
    topic_list = [
        NewTopic(
            name=f"{(settings.KAFKA_TOPIC_PRODUCT).strip()}",
            num_partitions=2,
            replication_factor=1,
        ),
        NewTopic(
            name=f"{(settings.KAFKA_TOPIC_STOCK_LEVEL_CHECK).strip()}",
            num_partitions=2,
            replication_factor=1,
        ),
    ]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only=False)
        logger.info("Kafka topics created successfully")
    except Exception as e:
        logger.error(f"Error creating topics: {e}")
    finally:
        await admin_client.close()


def product_to_proto(product: models.ProductBase) -> product_pb2.Product:
    return product_pb2.Product(
        product_id=product.product_id,
        name=product.name,
        description=product.description,
        price=product.price,
        is_available=product.is_available,
        category=product.category,
    )


async def send_kafka_message(topic: str, message):
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await producer.start()
    print("IN PRODUCER IT IS RECIEVING THIS  " + str(message))
    try:
        await producer.send_and_wait(topic, message)
        logger.info(f"Message sent to topic {topic}")
    finally:
        await producer.stop()


async def consume_messages(topic: str, group_id: str):
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=group_id,
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            try:
                new_msg = product_pb2.Product()
                new_msg.ParseFromString(msg.value)
                logger.info(f"Parsed message on consumer side: {new_msg}")
                yield new_msg
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                logger.error(f"Failed to parse message: {msg.value}")

    finally:
        await consumer.stop()


async def consume_messages_stock(topic: str, group_id: str):
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=group_id,
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            try:
                new_msg = product_pb2.Inventory()
                new_msg.ParseFromString(msg.value)
                logger.info(f"Parsed message on consumer side: {new_msg}")
                yield new_msg
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                logger.error(f"Failed to parse message: {msg.value}")

    finally:
        await consumer.stop()


async def retry_async(coro, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return await coro()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds..."
            )
            await asyncio.sleep(delay)
