from sqlmodel import SQLModel, create_engine, Session
from app import settings

connection_string: str = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

engine = create_engine(connection_string, connect_args={}, pool_recycle=300)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
