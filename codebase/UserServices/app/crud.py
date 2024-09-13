from typing import Optional, List, Union
from sqlmodel import Session, select
from app.models import UserClass


async def get_user_id(
    session: Session, user_id: Union[str, int]
) -> Optional[UserClass]:
    user_id = int(user_id)
    return session.exec(select(UserClass).where(UserClass.user_id == user_id)).first()


async def get_user_by_username(session: Session, username: str) -> Optional[UserClass]:
    return session.exec(select(UserClass).where(UserClass.username == username)).first()


async def get_user_by_email(session: Session, email: str) -> Optional[UserClass]:
    user = session.exec(select(UserClass).where(UserClass.email == email)).first()
    if user:
        return user
    else:
        return None


async def get_all_users(session: Session) -> List[UserClass]:
    return list(session.exec(select(UserClass)).all())
