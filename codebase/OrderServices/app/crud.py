#crud.py
import logging
from typing import Optional, List
from app.models import OrdersBase, OrdersCreate, Orders, OrdersUpdate
from sqlmodel import Session, select
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create a new order
async def create_order(
    session: Session, order_data: OrdersCreate, user_id: str, product_id: str
) -> Orders:
    new_order = Orders(
        order_id=order_data.order_id,
        product_id=product_id,
        user_id=user_id,
        quantity=order_data.quantity,
        shipping_address=order_data.shipping_address,
        customer_notes=order_data.customer_notes,
        order_status="In_progress",
        payment_status="Pending",
    )
    session.add(new_order)
    session.commit()
    session.refresh(new_order)
    return new_order


# Retrieve a single order by order_id
async def get_order(session: Session, order_id: str) -> Optional[Orders]:
    order = session.exec(select(Orders).where(Orders.order_id == order_id)).first()
    if order is None:
        logger.error(f"Order with ID {order_id} not found.")
        return None
    else:
        return order

# Retrieve all orders for a given user
async def get_orders_by_user(session: Session, user_id: str) -> List[Orders]:
    return list(session.exec(select(Orders).where(Orders.user_id == user_id)).all())

# Retrieve all orders
async def get_all_orders(session: Session) -> List[Orders]:
    return list(session.exec(select(Orders)).all())

# Update an order
async def update_order(
    session: Session, order_id: str, order_data: OrdersUpdate
) -> Optional[Orders]:
    db_order = await get_order(session, order_id)
    if db_order:
        updated_order = OrdersUpdate(
            quantity=order_data.quantity,
            shipping_address=order_data.shipping_address,
            customer_notes=order_data.customer_notes,
            order_status=order_data.order_status,
            payment_status=order_data.payment_status,
        )
        data = updated_order.model_dump(exclude_unset=True)
        db_order.sqlmodel_update(data)
        session.add(db_order)
        session.commit()
        session.refresh(db_order)
        return db_order
    else:
        logger.error(f"Product with ID {order_id} not found.")
# Delete an order
async def delete_order(session: Session, order_id: str) -> Optional[Orders]:
    db_order = await get_order(session, order_id)
    if db_order:
        session.delete(db_order)
        session.commit()
        return db_order
    return None
