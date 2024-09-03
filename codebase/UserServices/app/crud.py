from typing import Optional
from sqlmodel import Session, select
from app.models import UserClass


async def get_user_id(session: Session, user_id: str) -> Optional[UserClass]:
    return session.exec(select(UserClass).where(UserClass.user_id == user_id)).first()


async def get_user_by_username(session: Session, username: str) -> Optional[UserClass]:
    return session.exec(select(UserClass).where(UserClass.username == username)).first()


async def get_user_by_email(session: Session, email: str) -> Optional[UserClass]:
    return session.exec(select(UserClass).where(UserClass.email == email)).first()
