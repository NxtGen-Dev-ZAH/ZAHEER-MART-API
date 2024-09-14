# db.py
from app import settings
from sqlmodel import SQLModel, create_engine, Session
# Database setup
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)
#  Creating Engine
engine = create_engine(connection_string, pool_recycle=300, pool_size=10, echo=True)
#  Function to create tables
def create_table():
    SQLModel.metadata.create_all(engine)
def get_session():
    with Session(engine) as session:
        yield session
