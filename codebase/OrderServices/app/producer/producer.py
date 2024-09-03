from sqlmodel import SQLModel, Field, create_engine, select, Session
from google.protobuf.json_format import MessageToDict
from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from typing import Annotated
from aiokafka import AIOKafkaConsumer
from app.router import user
from app import order_pb2
from app import settings
from app import db, kafka, models, auth
from app.consumer import main

import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def publish_order_created(product_id: str, item: models.OrdersCreate, user_proto):
    order_proto = order_pb2.Order(
        order_id=item.order_id,
        user_id=str(user_proto.user_id),
        username=user_proto.username,
        email=user_proto.email,
        product_id=product_id,
        quantity=item.quantity,
        shipping_address=item.shipping_address,
        customer_notes=item.customer_notes,
        order_status=order_pb2.OrderStatus.IN_PROGRESS,
        payment_status=order_pb2.PaymentStatus.PENDING,
        option=order_pb2.SelectOption.CREATE,
    )
    serialized_order = order_proto.SerializeToString()
    await kafka.send_message_producer(f"{settings.KAFKA_TOPIC_ORDER}", serialized_order)


async def publish_order_update(order_id: str, order: models.OrdersUpdate, user_id: str):
    order_proto = order_pb2.Order(
        order_id=str(order_id),
        user_id=user_id,
        order_status=order.order_status,
        payment_status=order.payment_status,
        quantity=order.quantity,
        shipping_address=order.shipping_address,
        customer_notes=order.customer_notes,
        option=order_pb2.SelectOption.UPDATE,
    )
    serialized_order = order_proto.SerializeToString()
    await kafka.send_message_producer(settings.KAFKA_TOPIC_ORDER, serialized_order)
    logger.info(f"Order update message sent for order ID: {order_id}")


async def publish_order_deleted(order_id: str, user_id: str):
    order_proto = order_pb2.Order(
        order_id=str(order_id),
        user_id=user_id,
        option=order_pb2.SelectOption.DELETE,
    )
    serialized_order = order_proto.SerializeToString()
    await kafka.send_message_producer(settings.KAFKA_TOPIC_ORDER, serialized_order)
    logger.info(f"Order delete message sent for order ID: {order_id}")


async def consume_message_response_get():
    consumer = AIOKafkaConsumer(
        f"{settings.KAFKA_TOPIC_ORDER}",
        bootstrap_servers=f"{settings.BOOTSTRAP_SERVER}",
        group_id=f"{settings.KAFKA_CONSUMER_GROUP_ID_FOR_ORDER}",
        auto_offset_reset="earliest",
    )
    await kafka.retry_async(consumer.start)
    try:
        async for msg in consumer:
            logger.info(f"message from consumer in producer  : {msg}")
            try:
                new_msg = order_pb2.Order()
                new_msg.ParseFromString(msg.value)
                logger.info(f"new_msg on producer side:{new_msg}")
                return new_msg
            except Exception as e:
                logger.error(f"Error Processing Message: {e} ")
    finally:
        await consumer.stop()


# verify_token:Annotated[models.User,Depends(auth.verify_access_token)]
