from fastapi import HTTPException
from app.models import UserClass, UserCreate, USERLOGIN, Usertoken
from app import kafka, settings, user_pb2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def publish_user_register(register: UserCreate):
    try:
        user_proto = user_pb2.User(
            shipping_address=register.shipping_address,
            username=register.username,
            email=register.email,
            password=register.password,
            phone=register.phone,
            option=user_pb2.SelectOption.REGISTER,
        )
        serialized_user = user_proto.SerializeToString()
        await kafka.send_and_wait(settings.KAFKA_TOPIC_USER, serialized_user)
        return {"message": "User registration request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def publish_user_login(login: USERLOGIN):
    try:
        user_proto = user_pb2.User(
            username=login.username,
            password=login.password,
            option=user_pb2.SelectOption.LOGIN,
        )
        serialized_user = user_proto.SerializeToString()
        await kafka.send_message(settings.KAFKA_TOPIC_USER, serialized_user)
        return {"message": "User login In producer"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def publish_user_refresh(login: Usertoken):
    try:
        user_proto = user_pb2.User(
            username=login.username,
            email=login.email,
            option=user_pb2.SelectOption.REFRESH_TOKEN,
        )
        serialized_user = user_proto.SerializeToString()
        await kafka.send_message(settings.KAFKA_TOPIC_USER, serialized_user)
        return {"message": "Refresh token request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def publish_user_verify(login: Usertoken):
    try:
        user_proto = user_pb2.User(
            username=login.username,
            email=login.email,
            option=user_pb2.SelectOption.CURRENT_USER,
        )
        serialized_user = user_proto.SerializeToString()
        await kafka.send_message(settings.KAFKA_TOPIC_USER, serialized_user)
        return {"message": "Verify user request sent successfully"}
    except Exception as e:
        logger.error(f"Failed to produce message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
