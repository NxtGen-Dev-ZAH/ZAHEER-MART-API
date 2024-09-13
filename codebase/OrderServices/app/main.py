import asyncio
from contextlib import asynccontextmanager
from typing import Annotated, List
from fastapi import Depends, FastAPI, HTTPException
from app import auth, models, order_pb2, settings
from app import kafka, crud, db
from app.db import get_session
from app.kafka import create_topic
from app.producer import producer
from app.router import user
from sqlmodel import Session
from app.consumer import main


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_table()
    await create_topic()
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(main.start_consuming())
    task2 = loop.create_task(main.start_consuming_payment())
    try:
        yield
    finally:
        for task in [task1, task2]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app: FastAPI = FastAPI(
    lifespan=lifespan, dependencies=[Depends(auth.verify_access_token)]
)

app.include_router(router=user.user_router)


# Home Endpoint
@app.get("/")
async def read_root():
    return {"message": "Order Management Service"}


@app.get("/orders", response_model=list[models.Orders])
async def get_all_orders_details(
    session: Annotated[Session, Depends(get_session)],
    verify_token: Annotated[models.User, Depends(auth.verify_access_token)],
):
    return await crud.get_all_orders(session)


@app.get("/order/{order_id}", response_model=models.Orders)
async def get_order_detail(
    order_id: str,
    session: Annotated[Session, Depends(get_session)],
    verify_token: Annotated[models.User, Depends(auth.verify_access_token)],
):
    return await crud.get_order(session, order_id)


@app.post("/products/", response_model=models.OrdersBase)
async def create_product(
    order: models.OrdersCreate,
    product_id: str,
    verify_token: Annotated[models.User, Depends(auth.verify_access_token)],
):
    user_proto = order_pb2.User(
        username=verify_token,
        service=order_pb2.SelectService.ORDER,
        option=order_pb2.SelectOption.CURRENT_USER,
    )
    serialized_user = user_proto.SerializeToString()
    await kafka.send_message_producer(
        settings.KAFKA_TOPIC_REQUEST_TO_USER, serialized_user
    )

    user_proto = await kafka.consume_message_from_user_service()

    await producer.publish_order_created(product_id, order, user_proto)
    return order


@app.put("/order/{order_id}", response_model=models.Orders)
async def update_order(
    order_id: str,
    order: models.OrdersUpdate,
    session: Annotated[Session, Depends(get_session)],
    verify_token: Annotated[models.User, Depends(auth.verify_access_token)],
):
    await producer.publish_order_update(order_id, order, str(verify_token.user_id))
    order_data = await crud.get_order(session, order_id)
    if order_data is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_data


@app.delete("/order/{order_id}", response_model=dict)
async def delete_order(
    order_id: str,
    session: Annotated[Session, Depends(get_session)],
    verify_token: Annotated[models.User, Depends(auth.verify_access_token)],
):
    await producer.publish_order_deleted(order_id, str(verify_token.user_id))
    order = await crud.get_order(session, order_id)
    if order is None:
        return {"Order Deleted": f"Order id {order_id} is not found"}
    else:
        return {"Order not deleted": f" {order_id} is found"}


# Endpoint to get all the orders
# @app.get("/orders", response_model=list[Orders])
# async def get_all_orders(
#     producer: Annotated[AIOKafkaProducer, Depends(send_message_producer)],
#     verify_token: Annotated[models.User, Depends(auth.verify_access_token)],
# ):
#     order_proto = order_pb2.Order(
#         user_id=str(verify_token.user_id), option=order_pb2.SelectOption.GET_ALL
#     )
#     serialized_order = order_proto.SerializeToString()
#     await producer.send_and_wait(f"{settings.KAFKA_TOPIC_ORDER}", serialized_order)

#     order_list_proto = await consume_message_response_get_all()

#     order_list = [
#         {
#             "id": order.id,
#             "user_id": str(order.user_id),
#             "order_id": str(order.order_id),
#             "product_id": str(order.product_id),
#             "quantity": order.quantity,
#             "shipping_address": order.shipping_address,
#             "customer_notes": order.customer_notes,
#         }
#         for order in order_list_proto.orders
#     ]
#     return order_list


#  Endpoint to get the single order based on endpoint
# @app.get("/order/{order_id}", response_model=dict)
# async def get_a_order(
#     order_id: UUID,
#     producer: Annotated[AIOKafkaProducer, Depends(send_message_producer)],
#     verify_token: Annotated[models.User, Depends(auth.verify_access_token)],
# ):
#     order_proto = order_pb2.Order(
#         order_id=str(order_id),
#         user_id=str(verify_token.user_id),
#         option=order_pb2.SelectOption.GET,
#     )
#     serialized_order = order_proto.SerializeToString()
#     await producer.send_and_wait(f"{settings.KAFKA_TOPIC_ORDER}", serialized_order)

#     order_proto = await consume_message_response_get()

#     if order_proto.error_message or order_proto.http_status_code:
#         raise HTTPException(
#             status_code=order_proto.http_status_code, detail=order_proto.error_message
#         )
#     else:
#         return {
#             "id": order_proto.id,
#             "user_id": str(order_proto.user_id),
#             "order_id": str(order_proto.order_id),
#             "product_id": str(order_proto.product_id),
#             "quantity": order_proto.quantity,
#             "shipping_address": order_proto.shipping_address,
#             "customer_notes": order_proto.customer_notes,
#         }


# order_proto = await producer.consume_message_response_get()

# if order_proto.quantity is None:
#     order_proto.quantity = 0

# if order_proto.error_message and order_proto.http_status_code:
#     raise HTTPException(
#         status_code=order_proto.http_status_code, detail=order_proto.error_message
#     )
# elif order_proto.error_message:
#     return {"Order not updated": f"{order_proto.error_message}"}
# else:
#     return {
#         "Order Updated": {
#             "id": order_proto.id,
#             "user_id": str(order_proto.user_id),
#             "order_id": str(order_proto.order_id),
#             "product_id": str(order_proto.product_id),
#             "quantity": order_proto.quantity,
#             "shipping_address": order_proto.shipping_address,
#             "customer_notes": order_proto.customer_notes,
#         }
#     }
