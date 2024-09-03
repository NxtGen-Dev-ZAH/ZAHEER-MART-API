from app import kafka
from app.kafka import (
    consume_message_from_inventory_check,
    retry_async,
    send_message_producer,
)
from app.models import Orders, OrdersBase, OrdersCreate, OrdersUpdate
from sqlmodel import select, Session
from app import crud, settings, order_pb2, db

# import ".order.proto"
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_inventory_check(product_id, quantity, option):
    inventory_check_proto = order_pb2.Order(
        product_id=product_id, quantity=quantity, option=option
    )
    serialized_inventory_check = inventory_check_proto.SerializeToString()
    await send_message_producer(
        settings.KAFKA_TOPIC_INVENTORY_CHECK_REQUEST, serialized_inventory_check
    )
    inventory_check = await consume_message_from_inventory_check()
    return inventory_check


async def handle_create_order(new_msg):
    if new_msg.quantity > 0:
        with Session(db.engine) as session:
            inventory_check = await handle_inventory_check(
                new_msg.product_id, new_msg.quantity, order_pb2.SelectOption.CREATE
            )
            logger.info(f"Inventory check value: {inventory_check}")
            if inventory_check is not None:
                if (
                    inventory_check.is_product_available
                    and inventory_check.is_stock_available
                ):

                    created_order = await crud.create_order(
                        session, new_msg, new_msg.user_id, new_msg.product_id
                    )
                    return created_order
            else:
                logger.error("Insufficient inventory or stock.")
                return None
    else:
        logger.error(f"Invalid quantity: {new_msg.quantity}")
        return None


#  Function to handle update order request from producer side from where API is called to update order to database
async def handle_update_order(new_msg: OrdersUpdate, order_id: str):
    with Session(db.engine) as session:
        order = await crud.get_order(session, order_id)
        if order:
            # new_quantity = order.quantity - new_msg.quantity
            inventory_check = await handle_inventory_check(
                order.product_id, new_msg.quantity, order_pb2.SelectOption.UPDATE
            )

            if inventory_check is not None:
                if inventory_check.is_stock_available:
                    updated_order = await crud.update_order(session, order_id, new_msg)
                    return updated_order
            else:
                logger.error("Insufficient stock.")
                return None
        else:
            logger.error("Order not found.")
            return None


##################################### Delete ORDER ################################


async def handle_delete_order(order_id):
    with Session(db.engine) as session:
        order = await crud.get_order(session, order_id)
        if order:
            if order.payment_status == "Payment Done":
                logger.info("Order cannot be deleted as payment is done")
            else:
                await handle_inventory_check(
                    order.product_id, order.quantity, order_pb2.SelectOption.DELETE
                )
                deleted_order = await crud.delete_order(session, order_id)
                if deleted_order:
                    logger.info(
                        f"========= Order deleted and confirmation sent back: {order} =================="
                    )
        else:
            logger.info("================== Order not found ===========")


async def process_message(order: order_pb2.Order):
    try:
        if order.option == order_pb2.SelectOption.CREATE:
            await handle_create_order(order)
        elif order.option == order_pb2.SelectOption.UPDATE:
            await handle_update_order(order, order.order_id)
        elif order.option == order_pb2.SelectOption.DELETE:
            await handle_delete_order(order.order_id)
        else:
            logger.warning(f"Unknown option: {order.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def start_consuming():
    try:
        async for message in kafka.consume_messages_order(
            settings.KAFKA_TOPIC_ORDER, settings.KAFKA_CONSUMER_GROUP_ID_FOR_ORDER
        ):
            await process_message(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


async def handle_order_payment(session: Session, new_msg: order_pb2.Payment):
    user_orders = session.exec(
        select(Orders).where(Orders.user_id == (new_msg.user_id))
    ).all()

    order = next(
        (order for order in user_orders if order.order_id == (new_msg.order_id)),
        None,
    )

    if order:
        logger.info(f"Order found: {order}")
        await handle_inventory_check(
            order.product_id,
            order.quantity,
            order_pb2.SelectOption.PAYMENT_DONE,
        )

        order.order_status = "Completed"
        order.payment_status = "Payment Done"
        session.add(order)
        session.commit()
    else:
        logger.warning(f"Order not found for order_id: {new_msg.order_id}")


async def process_message_payment(msg: order_pb2.Payment):
    if msg.payment_status == order_pb2.PaymentStatus.PAID:
        with Session(db.engine) as session:
            await handle_order_payment(session, msg)


async def start_consuming_payment():
    try:
        async for message in kafka.consume_messages_payment(
            settings.KAFKA_TOPIC_PAYMENT_DONE_FROM_PAYMENT,
            settings.KAFKA_CONSUMER_GROUP_ID_FOR_RESPONSE_FROM_PAYMENT,
        ):
            await process_message_payment(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


# Function to consume message from the APIs on the producer side and perform functionalities according to the request made by APIs


#   Function to handle get all orders request from producer side from where API is called to get all orders
# async def handle_get_all_orders(user_id):
#     with Session(db.engine) as session:
#         orders_list = session.exec(
#             select(Orders).where(Orders.user_id == user_id)
#         ).all()
#         orders_list_proto = order_pb2.OrderList()
#         for order in orders_list:
#             order_proto = order_pb2.Order(
#                 id=order.id,
#                 user_id=str(order.user_id),
#                 order_id=str(order.order_id),
#                 product_id=str(order.product_id),
#                 quantity=order.quantity,
#                 shipping_address=order.shipping_address,
#                 customer_notes=order.customer_notes,
#             )
#             orders_list_proto.orders.append(order_proto)
#         serialized_order_list = orders_list_proto.SerializeToString()
#         await send_message_producer(settings.KAFKA_TOPIC_GET, serialized_order_list)
#         logger.info(f"List of orders sent back from database: {orders_list_proto}")


# #  Function to handle get order request from producer side from where API is called to get an order
# async def handle_get_order(new_msg):
#     with Session(db.engine) as session:
#         user_orders = session.exec(
#             select(Orders).where(Orders.user_id == uuid.UUID(new_msg.user_id))
#         ).all()
#         order = next(
#             (
#                 order
#                 for order in user_orders
#                 if order.order_id == uuid.UUID(new_msg.order_id)
#             ),
#             None,
#         )
#         if order:
#             order_proto = order_pb2.Order(
#                 id=order.id,
#                 user_id=str(order.user_id),
#                 order_id=str(order.order_id),
#                 product_id=str(order.product_id),
#                 quantity=order.quantity,
#                 shipping_address=order.shipping_address,
#                 customer_notes=order.customer_notes,
#             )
#             serialized_order = order_proto.SerializeToString()
#             await send_message_producer(settings.KAFKA_TOPIC_GET, serialized_order)
#             logger.info(f"Order sent back from database: {order_proto}")
#         else:
#             order_proto = order_pb2.Order(
#                 error_message=f"No Order with order_id: {new_msg.order_id} found!",
#                 http_status_code=400,
#             )
#             serialized_order = order_proto.SerializeToString()
#             await send_message_producer(settings.KAFKA_TOPIC_GET, serialized_order)


#                         if new_msg.option == order_pb2.SelectOption.GET_ALL:
#                 await handle_get_all_orders(new_msg.user_id)
#             elif new_msg.option == order_pb2.SelectOption.GET:
#                 await handle_get_order(new_msg)


#             if order:
#                 order_proto = order_pb2.Order(
#                     id=order.id,
#                     order_id=order.order_id,
#                     product_id=str(order.product_id),
#                     user_id=str(order.user_id),
#                     username=new_msg.username,
#                     email=new_msg.email,
#                     quantity=order.quantity,
#                     shipping_address=order.shipping_address,
#                     customer_notes=order.customer_notes,
#                     option=order_pb2.SelectOption.CREATE,
#                 )
#                 serialized_order = order_proto.SerializeToString()
#                 await send_message_producer(
#                     settings.KAFKA_TOPIC_GET, serialized_order
#                 )
#                 logger.info(f"Order added to database and sent back: {order_proto}")
#             else:
#                     order_proto = order_pb2.Order(
#                         error_message=f"No order having product_id: {new_msg.product_id} created!",
#                         http_status_code=404,
#                     )
#                     serialized_order = order_proto.SerializeToString()
#                     await send_message_producer(
#                         settings.KAFKA_TOPIC_GET, serialized_order
#                     )
#         else:
#             order_proto = order_pb2.Order(
#                 error_message=f"Requested Quantity of product is not available",
#                 http_status_code=404,
#             )
#             serialized_order = order_proto.SerializeToString()
#             await send_message_producer(settings.KAFKA_TOPIC_GET, serialized_order)
# else:
#     order_proto = order_pb2.Order(
#         error_message=f"In order to proceed with order you need to specify the no of items you need to buy",
#         http_status_code=404,
#     )
#     serialized_order = order_proto.SerializeToString()
#     await send_message_producer(settings.KAFKA_TOPIC_GET, serialized_order)


# #  Function to handle delete product request from producer side from where API is called to delete product from database
# async def handle_delete_order(new_msg):
#     with Session(db.engine) as session:
#         user_orders = session.exec(
#             select(Orders).where(Orders.user_id == uuid.UUID(new_msg.user_id))
#         ).all()
#         order = next(
#             (
#                 order
#                 for order in user_orders
#                 if order.order_id == uuid.UUID(new_msg.order_id)
#             ),
#             None,
#         )
#         if order:
#             if order.payment_status == "Payment Done":
#                 order_proto = order_pb2.Order(
#                     message=f"Order with order_id: {new_msg.order_id} can not be deleted! as payment is done and it has been dispatched from the warehouse",
#                 )
#                 serialized_product = order_proto.SerializeToString()
#                 await send_message_producer(
#                     settings.KAFKA_TOPIC_GET, serialized_product
#                 )

#             else:
#                 await handle_inventory_check(
#                     order.product_id, order.quantity, order_pb2.SelectOption.DELETE
#                 )
#                 session.delete(order)
#                 session.commit()
#                 order_proto = order_pb2.Order(
#                     message=f"Order with order_id: {new_msg.order_id} deleted!",
#                 )
#                 serialized_product = order_proto.SerializeToString()
#                 await send_message_producer(
#                     settings.KAFKA_TOPIC_GET, serialized_product
#                 )
#                 logger.info(f"Order deleted and confirmation sent back: {order_proto}")
#         else:
#             order_proto = order_pb2.Order(
#                 error_message=f"No Order with order_id: {new_msg.order_id} found!",
#                 http_status_code=404,
#             )
#             serialized_product = order_proto.SerializeToString()
#             await send_message_producer(settings.KAFKA_TOPIC_GET, serialized_product)
