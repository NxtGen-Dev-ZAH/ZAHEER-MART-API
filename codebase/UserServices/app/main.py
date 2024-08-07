from typing import Annotated
from aiokafka import AIOKafkaProducer
from fastapi import Depends, FastAPI, HTTPException
from contextlib import asynccontextmanager
import asyncio
from app import db, models, settings, user_pb2, kafkafile
from codebase.UserServices.app import main
from uuid import UUID
import logging
from app.consumer import main

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_db_and_tables()
    await kafkafile.create_topic()
    loop = asyncio.get_event_loop()
    task = loop.create_task(main.consume_message_request())
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
    return {"Hello": "User Service"}


@app.post("/user/register")
async def register_user(register: models.UserCreate,producer: Annotated[AIOKafkaProducer, Depends(kafkafile.create_producer)]):
    try:
        user_proto = user_pb2.User(
            username=register.username,
            email=register.email,
            password=register.password,
            phone=register.phone,
            option=user_pb2.SelectOption.REGISTER,
        )
        serialized_user = user_proto.SerializeToString()
        await producer.send_and_wait(settings.KAFKA_TOPIC, serialized_user)
        return {"message": "User registration request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/user/login")
async def login_user(login: models.UserCreate,producer: Annotated[AIOKafkaProducer, Depends(kafkafile.create_producer)]):
    try:
        user_proto = user_pb2.User(

            username=login.username,
            password=login.password,
            option=user_pb2.SelectOption.LOGIN,
        )
        serialized_user = user_proto.SerializeToString()
        await producer.send_and_wait(settings.KAFKA_TOPIC, serialized_user)
        return {"message": "User login request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/user/refresh_token")
async def refresh_token(login: models.UserCreate,producer: Annotated[AIOKafkaProducer, Depends(kafkafile.create_producer)]):
    try:
        user_proto = user_pb2.User(
            username=login.username,
            email=login.email,
            option=user_pb2.SelectOption.REFRESH_TOKEN,
        )
        serialized_user = user_proto.SerializeToString()
        await producer.send_and_wait(settings.KAFKA_TOPIC, serialized_user)
        return {"message": "Refresh token request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/user/verify_user")
async def verify_user(login: models.UserCreate,producer: Annotated[AIOKafkaProducer, Depends(kafkafile.create_producer)]):
    try:
        user_proto = user_pb2.User(
            username=login.username,
            email=login.email,
            option=user_pb2.SelectOption.CURRENT_USER,
        )
        serialized_user = user_proto.SerializeToString()
        await producer.send_and_wait(settings.KAFKA_TOPIC, serialized_user)
        return {"message": "Verify user request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/user/create")
async def create_user(user: models.User,producer: Annotated[AIOKafkaProducer, Depends(kafkafile.create_producer)]):
    try:
        user_proto = user_pb2.User(
            username=user.username,
            email=user.email,
            password=user.password,
            shipping_address=user.shipping_address,
            phone=user.phone,
            option=user_pb2.SelectOption.CREATE,
        )
        serialized_user = user_proto.SerializeToString()
        await producer.send_and_wait(settings.KAFKA_TOPIC, serialized_user)
        return {"message": "User creation request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/user/{user_id}")
async def read_user(user_id: UUID,producer: Annotated[AIOKafkaProducer, Depends(kafkafile.create_producer)]):
    try:
        user_proto = user_pb2.User(
            user_id=str(user_id), option=user_pb2.SelectOption.READ
        )
        serialized_user = user_proto.SerializeToString()
        await producer.send_and_wait(settings.KAFKA_TOPIC, serialized_user)
        return {"message": "User read request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/user/{user_id}")
async def update_user(user_id: UUID, user: models.User,producer: Annotated[AIOKafkaProducer, Depends(kafkafile.create_producer)]):
    try:
        user_proto = user_pb2.User(
            user_id=str(user_id),
            username=user.username,
            email=user.email,
            shipping_address=user.shipping_address,
            phone=user.phone,
            password=user.password if user.password else "",
            option=user_pb2.SelectOption.UPDATE,
        )
        serialized_user = user_proto.SerializeToString()
        await producer.send_and_wait(settings.KAFKA_TOPIC, serialized_user)
        return {"message": "User update request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/user/{user_id}")
async def delete_user(user_id: UUID,producer: Annotated[AIOKafkaProducer, Depends(kafkafile.create_producer)]):
    try:
        user_proto = user_pb2.User(
            user_id=str(user_id), option=user_pb2.SelectOption.DELETE
        )
        serialized_user = user_proto.SerializeToString()
        await producer.send_and_wait(settings.KAFKA_TOPIC, serialized_user)
        return {"message": "User deletion request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
