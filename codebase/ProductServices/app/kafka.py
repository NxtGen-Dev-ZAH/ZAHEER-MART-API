import asyncio
from aiokafka import AIOKafkaConsumer,AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient,NewTopic
from app import settings , main,product_pb2

async def retry_async(func, retries=5, delay=2, *args, **kwargs):
    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            main.logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise

async def create_topic ():
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers= f"{settings.BOOTSTRAP_SERVER}"
    )
    await retry_async(admin_client.start)
    topic_list = [
        NewTopic(name=f"{(settings.KAFKA_TOPIC).strip()}", num_partitions=2, replication_factor=1),
        NewTopic(name=f"{(settings.KAFKA_TOPIC_GET).strip()}", num_partitions=2, replication_factor=1)
    ]
    try:
        await admin_client.create_topics(new_topics=topic_list, validate_only= False)
    except Exception as e:
        main.logger.error ( "Error creating topics:: {e}")
    finally:
        await admin_client.close()

async def consume_message_response_get_all():
    consumer = AIOKafkaConsumer(
        f"{settings.KAFKA_TOPIC_GET}",
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT_GET}",
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            main.logger.info(f"message from consumer : {msg}")
            try:
                new_msg = product_pb2.ProductList()
                new_msg.ParseFromString(msg.value)
                main.logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                main.logger.error(f"Error Processing Message: {e} ")
    finally:
        await consumer.stop()

async def consume_message_response():
    consumer = AIOKafkaConsumer(
        f"{settings.KAFKA_TOPIC_GET}",
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT_GET}",
        auto_offset_reset="earliest",
    )
    await retry_async(consumer.start)
    try:
        async for msg in consumer:
            main.logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = product_pb2.Product()
                new_msg.ParseFromString(msg.value)
                main.logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                main.logger.error(f"Error Processing Message: {e} ")
    finally:
        await consumer.stop()


#  Function to produce message. I will work as a dependency injection for APIs
async def create_produce():
    producer = AIOKafkaProducer(bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}")
    await retry_async(producer.start)
    try:
        yield producer
    finally:
        await producer.stop()
