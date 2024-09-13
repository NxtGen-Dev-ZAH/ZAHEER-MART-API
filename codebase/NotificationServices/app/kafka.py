from app import settings
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer  # type: ignore
import asyncio
import logging
from app import notification_pb2


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Retry utility
async def retry_async(func, retries=5, delay=2):
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise


#  Function to produce message.
async def produce_message(topic, message):
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await retry_async(producer.start)
    try:
        await producer.send_and_wait(topic, message)
    finally:
        await producer.stop()


async def consume_message_user(TOPIC: str, consumer_id: str):
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=consumer_id,
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = notification_pb2.User()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg we get from user_service :{new_msg}")
                yield new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")
    finally:
        await consumer.stop()


async def consume_message_payment(TOPIC: str, consumer_id: str):
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=consumer_id,
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = notification_pb2.Payment()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg we get from payment services :{new_msg}")
                yield new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")
    finally:
        await consumer.stop()


async def consume_message_order(TOPIC: str, consumer_id: str):
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=consumer_id,
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = notification_pb2.Order()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg we get from order_service :{new_msg}")
                yield new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")
    finally:
        await consumer.stop()
