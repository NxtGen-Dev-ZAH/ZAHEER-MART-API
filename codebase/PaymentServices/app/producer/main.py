from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from typing import Annotated
from app.router import user
from app import payment_pb2
from app import settings
from app import db, kafka, models, auth
from app.consumer import main
from app.kafka import retry_async, send_kafka_message

import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def publish_payment_request(
    payment_request_detail: models.PaymentRequest, verify_token: str
):
    user_proto = payment_pb2.User(
        username=verify_token,
        service=payment_pb2.SelectService.PAYMENT,
        option=payment_pb2.SelectOption.CURRENT_USER,
    )
    serialized_user = user_proto.SerializeToString()
    await send_kafka_message(settings.KAFKA_TOPIC_REQUEST_TO_USER, serialized_user)

    user_proto = await main.consume_user_service_response()

    payment_proto = payment_pb2.Payment(
        user_id=user_proto.user_id,
        username=user_proto.username,
        email=user_proto.email,
        amount=payment_request_detail.amount,
        card_number=payment_request_detail.card_number,
        exp_month=payment_request_detail.exp_month,
        exp_year=payment_request_detail.exp_year,
        cvc=payment_request_detail.cvc,
        order_id=str(payment_request_detail.order_id),
    )
    serialized_payment = payment_proto.SerializeToString()
    await send_kafka_message(settings.KAFKA_TOPIC_PAYMENT, serialized_payment)
