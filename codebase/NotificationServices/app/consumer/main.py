from sqlmodel import Session
from app import settings
from aiokafka import AIOKafkaConsumer  # type: ignore
from app import notification_pb2, kafka, handle_email, db
import logging

from app.models import Notification


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def save_notification(notification: Notification):
    with Session(db.engine) as session:
        session.add(notification)
        session.commit()
        session.refresh(notification)
        logger.info(f"Notification saved: {notification.id}")


async def process_message_user(new_msg: notification_pb2.User):
    if new_msg.option == notification_pb2.SelectOption.REGISTER:
        body = f"""Hi {new_msg.username},
Welcome to Online Mart! You have successfully signed in. Explore our wide range of products and enjoy seamless shopping!"""
        subject = f"""New User Registration """
        await handle_email.send_email(
            body=body, subject=subject, user_email=new_msg.email
        )
        notification = Notification(
            user_id=new_msg.id,
            email=new_msg.email,
            username=new_msg.username,
            title=subject,
            message=body,
            notification_type="USER_REGISTRATION",
        )
        await save_notification(notification)


async def start_consuming_user():
    try:
        async for message in kafka.consume_message_user(
            settings.KAFKA_TOPIC_USER,
            settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_NEW_USER,
        ):
            await process_message_user(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


async def process_message_payment(new_msg: notification_pb2.Payment):
    if new_msg.payment_status == notification_pb2.PaymentStatus.PAID:
        body = f"""Hi {new_msg.username},
Thank you for your purchase! Your payment has been successfully processed. Your order has been dispatched and is on its way! """
        subject = (
            f"""Payment Confirmation and Order Dispatch Notification from Online Mart"""
        )
        await handle_email.send_email(
            body=body, subject=subject, user_email=new_msg.email
        )
        notification = Notification(
            user_id=new_msg.id,
            email=new_msg.email,
            username=new_msg.username,
            title=subject,
            message=body,
            notification_type="PAYMENT_CONFIRMATION",
        )
        await save_notification(notification)


async def start_consuming_payment():
    try:
        async for message in kafka.consume_message_payment(
            settings.KAFKA_TOPIC_USER,
            settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_PAYMENT_DONE,
        ):
            await process_message_payment(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


async def process_message_order(new_msg: notification_pb2.Order):
    if new_msg.option == notification_pb2.SelectOption.CREATE:
        body = f"""Hi {new_msg.username},
Thankyou for your order. Your order has been placed successfully.To Proceed, please make the payment. we will notify you once the payment is done."""
        subject = f"""Order Confirmation"""
        await handle_email.send_email(
            body=body, subject=subject, user_email=new_msg.email
        )
        notification = Notification(
            user_id=new_msg.id,
            email=new_msg.email,
            username=new_msg.username,
            title=subject,
            message=body,
            notification_type="ORDER_CONFIRMATION",
        )
        await save_notification(notification)


async def start_consuming_order():
    try:
        async for message in kafka.consume_message_order(
            settings.KAFKA_TOPIC_ORDER,
            settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_ORDER_CREATED,
        ):
            await process_message_order(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")
