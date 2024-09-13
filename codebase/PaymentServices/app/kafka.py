from app import settings
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer  # type: ignore
from aiokafka.admin import AIOKafkaAdminClient, NewTopic  # type: ignore
from app import payment_pb2
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Retry utility
async def retry_async(func, retries=5, delay=2):
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise


# Creating topic from code
async def create_topic():
    admin_client = AIOKafkaAdminClient(bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}")
    await retry_async(admin_client.start)
    topic_list = [
        NewTopic(
            name=f"{settings.KAFKA_TOPIC_PAYMENT}",
            num_partitions=2,
            replication_factor=1,
        ),
    ]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only=False)
    except Exception as e:
        logger.error("Error creating topics:: {e}")
    finally:
        await admin_client.close()


#  Function to consume  messages from user service
async def consume_message_from_user_service():
    consumer = AIOKafkaConsumer(
        f"{settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT}",
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_RESPONSE_FROM_USER}",
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = payment_pb2.User()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side of payment:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")
    finally:
        await consumer.stop()


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
                new_msg = payment_pb2.Payment()
                new_msg.ParseFromString(msg.value)
                logger.info(f"Parsed message on consumer side: {new_msg}")
                yield new_msg
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                logger.error(f"Failed to parse message: {msg.value}")

    finally:
        await consumer.stop()


async def consume_messages_order(topic: str, group_id: str):
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
                logger.info(f"Received message: {msg}")
                new_msg = payment_pb2.Order()
                new_msg.ParseFromString(msg.value)
                logger.info(f"Parsed message: {new_msg}")
                yield new_msg
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                logger.error(f"Failed to parse message: {msg.value}")
    finally:
        await consumer.stop()


async def consume_message_response_get():
    consumer = AIOKafkaConsumer(
        f"{settings.KAFKA_TOPIC_PAYMENT}",
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_PAYMENT}",
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = payment_pb2.Payment()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")
    finally:
        await consumer.stop()


#  Function to produce message.
async def send_kafka_message(topic, message):
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await retry_async(producer.start)
    try:
        await producer.send_and_wait(topic, message)
    finally:
        await producer.stop()
