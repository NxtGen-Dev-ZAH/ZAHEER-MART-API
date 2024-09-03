from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    email: str
    username: str
    title: str
    message: str
    notification_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = Field(default=False)