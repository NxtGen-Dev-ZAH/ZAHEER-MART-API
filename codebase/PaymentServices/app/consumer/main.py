# consumer:main.py
from app.stripe.payment import create_payment
from sqlmodel import  select, Session
from app import  crud, kafka, settings, payment_pb2, db, models
from app.payment_pb2 import Payment, PaymentStatus
from app.models import Payment,PaymentRequest

import logging
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# async def handle_order_payment(order_id: str):
#     with Session(db.engine) as session:
#         created_product = await crud.create_product_crud(session, order_id)
#         return created_product

async def process_order_message(message):
    if message.option == payment_pb2.SelectOption.CREATE:
        await handle_create_order(message)
    elif message.option == payment_pb2.SelectOption.DELETE:
        await handle_delete_order(message)

async def handle_create_order(message):
    payment = models.PAYMENTmodel(
        order_id=(message.order_id),
        user_id=(message.user_id),
    )
    with Session(db.engine) as session:
        session.add(payment)
        session.commit()

async def handle_delete_order(message):
    with Session(db.engine) as session:
        payment =crud.get_order(session,message.order_id)
        if payment:
            session.delete(payment)
            session.commit()

async def process_message(message):
    payment_request = create_payment_request(message)

    with Session(db.engine) as session:
        select_order = crud.get_order(session,message.order_id)
        
        if select_order:
            await handle_existing_payment(select_order, payment_request, message, session)
        else:
            await handle_missing_order(message)

def create_payment_request(message):
    if message.amount is None:
        message.amount = 0

    return PaymentRequest(
        amount=message.amount,
        card_number=message.card_number,
        exp_month=message.exp_month,
        exp_year=message.exp_year,
        cvc=message.cvc,
        order_id=str(message.order_id),
    )

async def handle_existing_payment(select_order, payment_request, message, session):
    payment_response = await create_payment(payment_request)

    if select_order.payment_status == "Payment Done":
        await send_duplicate_payment_message(message)
    else:
        await update_payment_status(select_order, payment_response, message, session)

async def handle_missing_order(message):
    payment_proto = payment_pb2.Payment(
        error_message="You haven't placed any order yet"
    )
    serialized_message = payment_proto.SerializeToString()
    await kafka.send_kafka_message(
        settings.KAFKA_TOPIC_PAYMENT, serialized_message
    )

async def send_duplicate_payment_message(message):
    payment_proto = payment_pb2.Payment(
        error_message=f"Payment Already Done",
    )
    serialized_message = payment_proto.SerializeToString()
    await kafka.send_kafka_message(
        settings.KAFKA_TOPIC_PAYMENT, serialized_message
    )

async def update_payment_status(select_order, payment_response, message, session):
    if payment_response == PaymentStatus.PAID:
        select_order.payment_status = "Payment Done"
        session.add(select_order)
        session.commit()
        await send_success_payment_message(select_order, message)
    else:
        select_order.payment_status = "Payment Failed"
        session.add(select_order)
        session.commit()
        await send_failed_payment_message(select_order)

async def send_success_payment_message(select_order, message):
    payment_proto = payment_pb2.Payment(
        user_id=str(message.user_id),
        order_id=str(select_order.order_id),
        username=message.username,
        email=message.email,
        payment_status=PaymentStatus.PAID,
    )
    serialized_message = payment_proto.SerializeToString()
    await kafka.send_kafka_message(
        settings.KAFKA_TOPIC_PAYMENT, serialized_message
    )

async def send_failed_payment_message(select_order):
    payment_proto = payment_pb2.Payment(
        order_id=str(select_order.order_id),
        payment_status=PaymentStatus.FAILED,
    )
    serialized_message = payment_proto.SerializeToString()
    await kafka.send_kafka_message(
        settings.KAFKA_TOPIC_PAYMENT, serialized_message
    )


async def start_consuming():
    try:
        async for message in kafka.consume_messages(
            settings.KAFKA_TOPIC_PAYMENT, settings.KAFKA_CONSUMER_GROUP_ID_FOR_PAYMENT
        ):
            await process_message(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")

async def start_order_consumer():
    try:
        async for message in kafka.consume_messages_order(
            settings.KAFKA_TOPIC_GET_FROM_ORDER,
            settings.KAFKA_CONSUMER_GROUP_ID_FOR_ORDER
        ):
            await process_order_message(message)
    except Exception as e:
        logger.error(f"Error in order consumer: {e}")

async def consume_user_service_response():
    return await kafka.consume_message_from_user_service()

async def consume_payment_response():
    return await kafka.consume_message_response_get()