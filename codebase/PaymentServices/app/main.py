import asyncio
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException
from app.consumer import main
from app.models import CheckoutRequest, Payment, User,PaymentRequest
from app import auth, db, kafka,  payment_pb2, settings
from app.producer.main import publish_payment_request
from app.router import user
import stripe


app: FastAPI = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_table()
    await kafka.create_topic()
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(main.start_consuming())
    task2 = loop.create_task(main.start_order_consumer())
    try:
        yield
    finally:
        for task in [task1, task2]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app.include_router(router=user.user_router)


@app.get("/")
async def root():
    return {"message": "Payment Management Service"}


#  Endpoint to add payment
@app.put("/payment", response_model=dict)

async def payment_request(
    payment_request_detail: PaymentRequest,
    verify_token: str = Depends(auth.verify_access_token),
):
    await publish_payment_request(payment_request_detail, verify_token)
    payment_proto = await main.consume_payment_response()

    if payment_proto.error_message:
        return {"Message": payment_proto.error_message}
    elif payment_proto.payment_status == payment_pb2.PaymentStatus.PAID:
        return {"payment_status": "Paid", "message": "Payment Successful"}
    else:
        return {"payment_status": "Pending", "message": "Payment Unsuccessful"}
    


@app.post("/create-checkout-session/")
async def create_checkout_session(checkout_request: CheckoutRequest):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': checkout_request.currency,
                    'product_data': {
                        'name': 'Your Product Name',
                    },
                    'unit_amount': checkout_request.amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://your-domain.com/success',
            cancel_url='https://your-domain.com/cancel',
        )
        return {"sessionId": session.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
