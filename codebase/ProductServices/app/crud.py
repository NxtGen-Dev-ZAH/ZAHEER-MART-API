# crud.py

from fastapi import HTTPException
from sqlmodel import Session, select
from app.models import ProductBase, Product, ProductUpdate
from typing import List, Optional
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_product_crud(session: Session, product2: ProductBase) -> Product:
    new_product = Product(
        product_id=product2.product_id,  # Replace with actual logic to generate a unique ID
        name=product2.name,
        description=product2.description,
        price=product2.price,
        is_available=product2.is_available,
        category=product2.category,
    )
    session.add(new_product)
    logger.info("data added to the database succesfully")
    session.commit()
    session.refresh(new_product)
    return new_product


async def get_product(session: Session, product_id: str) -> Optional[Product]:
    return session.exec(select(Product).where(Product.product_id == product_id)).first()


async def get_all_products(session: Session) -> List[Product]:
    return list(session.exec(select(Product)).all())


async def update_product(
    session: Session, product_id: str, product_data: ProductUpdate
) -> Optional[Product]:
    db_product = await get_product(session, product_id)
    if db_product:
        new_product = ProductUpdate(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            is_available=product_data.is_available,
            category=product_data.category,
        )
        data = new_product.model_dump(exclude_unset=True)
        db_product.sqlmodel_update(data)
        session.add(db_product)
        session.commit()
        session.refresh(db_product)
        return db_product
    else:
        logger.error(f"Product with ID {product_id} not found.")


async def delete_product(session: Session, product_id: str) -> Optional[Product]:
    db_product = await get_product(session, product_id)

    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    else:
        session.delete(db_product)
        session.commit()
        return db_product


# async def update_product_stock(session: Session, product_id: str, new_stock: int) -> Optional[Product]:
#     db_product = await get_product(session, product_id)
#     if db_product:
#         db_product.stock = new_stock
#         db_product.is_available = new_stock > 0
#         session.add(db_product)
#         session.commit()
#         session.refresh(db_product)
#     return db_product
