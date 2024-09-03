from typing import Annotated
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import asyncio

from sqlmodel import Session
from app import crud, db, models, settings, user_pb2, kafka
import logging
from app.consumer import main
from app.producer import producer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_db_and_tables()
    await kafka.create_topic()
    loop = asyncio.get_event_loop()
    task = loop.create_task(main.start_consuming())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"Hello": "Welcome To User Services "}


@app.get("/user/{useremail}")
async def read_user(useremail: str):
    with Session(db.engine) as session:
        return await crud.get_user_by_email(session, useremail)


@app.post("/user/register", response_model=models.UserClass)
async def register_user(register: models.UserCreate):
    await producer.publish_user_register(register)
    # return {"message": "User registration request sent successfully"}
    user = await read_user(register.email)
    return user


@app.post("/user/login", response_model=dict)
async def login_user(login: models.USERLOGIN):
    output = await producer.publish_user_login(login)
    return output


@app.post("/user/refresh_token", response_model=dict)
async def refresh_token(login: models.Usertoken):
    output = await producer.publish_user_refresh(login)
    return output


@app.post("/user/verify_user", response_model=dict)
async def verify_user(login: models.Usertoken):
    output = await producer.publish_user_verify(login)
    return output


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


# @app.post("/user/create")
# async def create_user(user: models.User):
#     try:
#         user_proto = user_pb2.User(
#             username=user.username,
#             email=user.email,
#             password=user.password,
#             shipping_address=user.shipping_address,
#             phone=user.phone,
#             option=user_pb2.SelectOption.CREATE,
#         )
#         serialized_user = user_proto.SerializeToString()
#         await producer.send_message(settings.KAFKA_TOPIC_USER, serialized_user)
#         return {"message": "User creation request sent successfully"}
#     except Exception as e:
#         logger.error(f"Failed to produce message: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")


# @app.get("/user/{user_id}")
# async def read_user(user_id: UUID):
#     try:
#         user_proto = user_pb2.User(
#             user_id=str(user_id), option=user_pb2.SelectOption.READ
#         )
#         serialized_user = user_proto.SerializeToString()
#         await producer.send_message(settings.KAFKA_TOPIC_USER, serialized_user)
#         return {"message": "User read request sent successfully"}
#     except Exception as e:
#         logger.error(f"Failed to produce message: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")


# @app.put("/user/{user_id}")
# async def update_user(user_id: UUID, user: models.User):
#     try:
#         user_proto = user_pb2.User(
#             user_id=str(user_id),
#             username=user.username,
#             email=user.email,
#             shipping_address=user.shipping_address,
#             phone=user.phone,
#             password=user.password if user.password else "",
#             option=user_pb2.SelectOption.UPDATE,
#         )
#         serialized_user = user_proto.SerializeToString()
#         await producer.send_message(settings.KAFKA_TOPIC_USER, serialized_user)
#         return {"message": "User update request sent successfully"}
#     except Exception as e:
#         logger.error(f"Failed to produce message: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")


# @app.delete("/user/{user_id}")
# async def delete_user(user_id: UUID):
#     try:
#         user_proto = user_pb2.User(
#             user_id=str(user_id), option=user_pb2.SelectOption.DELETE
#         )
#         serialized_user = user_proto.SerializeToString()
#         await producer.send_message(settings.KAFKA_TOPIC_USER, serialized_user)
#         return {"message": "User deletion request sent successfully"}
#     except Exception as e:
#         logger.error(f"Failed to produce message: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")
