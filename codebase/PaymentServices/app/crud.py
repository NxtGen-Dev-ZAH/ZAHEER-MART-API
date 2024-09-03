                
from typing import Optional
from fastapi import HTTPException
from sqlmodel import Session, select
from app.models import Payment

async def get_order(session: Session, order_id: str) -> Optional[Payment]:    
    return session.exec(select(Payment).where(Payment.order_id ==(order_id))).first()
 
