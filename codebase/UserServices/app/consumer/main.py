# consumer:main.py
from typing import Union
from sqlmodel import select, Session
from app import settings, user_pb2, db, kafka, auth, models, crud
from aiokafka import AIOKafkaConsumer
from datetime import timedelta
import logging
from app import kafka


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_user_in_db(username: str, email: str):
    logger.info("Checking user in DATABASE ")
    with Session(db.engine) as session:
        user = await crud.get_user_by_username(session, username)
        if not user:
            user = await crud.get_user_by_email(session, email)
            return user
        if user:
            logger.info("user with username is found in the database")
            return user
        else:
            return None


async def handle_register_user(new_msg):
    user = await check_user_in_db(new_msg.username, new_msg.email)
    if user:
        logger.info(f"User with these credentials already exists in database")
        return user

    else:
        user = models.UserClass(
            username=new_msg.username,
            email=new_msg.email,
            password=auth.hash_password(new_msg.password),
            phone=new_msg.phone,
            shipping_address=new_msg.shipping_address,
        )
        with Session(db.engine) as session:
            session.add(user)
            session.commit()
            logger.info(f"User added to database: {user}")
            session.refresh(user)
            logger.info(f"User added to database and sent back: {user}")


async def handle_login(new_msg):
    user = await check_user_in_db(new_msg.username, new_msg.password)
    if user is not None:
        if auth.verify_password(new_msg.password, user.password):
            expire_time = timedelta(minutes=settings.JWT_EXPIRY_TIME)
            access_token = auth.generate_token(
                data={"sub": user.username}, expires_delta=expire_time
            )
            expire_time_for_refresh_token = timedelta(days=15)
            refresh_token = auth.generate_token(
                data={"sub": user.email}, expires_delta=expire_time_for_refresh_token
            )

            user_proto = user_pb2.User(
                access_token=access_token,
                refresh_token=refresh_token,
                option=user_pb2.SelectOption.LOGIN,
            )
            logger.info(
                "================== User logged in this is his credentials =============",
                user_proto,
            )

            serialized_user = user_proto.SerializeToString()
            if new_msg.service == user_pb2.SelectService.PAYMENT:
                await kafka.send_message(
                    settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT,
                    serialized_user,
                )
            elif new_msg.service == user_pb2.SelectService.ORDER:
                await kafka.send_message(
                    settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER,
                    serialized_user,
                )
            logger.info(f"User logged in and sent back: {user_proto}")
        else:
            user_proto = user_pb2.User(
                error_message="Password is incorrect", http_status_code=401
            )
            serialized_user = user_proto.SerializeToString()
            if new_msg.service == user_pb2.SelectService.PAYMENT:
                await kafka.send_message(
                    settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT,
                    serialized_user,
                )
            elif new_msg.service == user_pb2.SelectService.ORDER:
                await kafka.send_message(
                    settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER,
                    serialized_user,
                )
    else:
        user_proto = user_pb2.User(
            error_message=f"{new_msg.username} is not registered in database",
            http_status_code=404,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )


async def handle_verify_user(new_msg):
    logger.info(
        f"Username we get at consumer on user service to verify it: {new_msg.username}"
    )
    user = await check_user_in_db(new_msg.username, new_msg.email)
    logger.info(f"detail of user after checking it from database: {user}")
    if not user:
        user_proto = user_pb2.User(
            error_message="User with these credentials do not exist in database",
            http_status_code=404,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )
    else:
        user_proto = user_pb2.User(
            user_id=str(user.user_id),
            username=user.username,
            email=user.email,
            password=user.password,
            shipping_address=user.shipping_address,
            phone=user.phone,
            option=user_pb2.SelectOption.CURRENT_USER,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )
        logger.info(f"User verified and username sent back: {user_proto}")


async def handle_refresh_token(new_msg):
    user = await check_user_in_db(new_msg.username, new_msg.email)
    if not user:
        user_proto = user_pb2.User(
            error_message="User with these credentials do not exist in database",
            http_status_code=404,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )
    else:
        expire_time = timedelta(minutes=settings.JWT_EXPIRY_TIME)
        access_token = auth.generate_token(
            data={"sub": user.username}, expires_delta=expire_time
        )
        expire_time_for_refresh_token = timedelta(days=15)
        refresh_token = auth.generate_token(
            data={"sub": user.email}, expires_delta=expire_time_for_refresh_token
        )
        user_proto = user_pb2.User(
            access_token=access_token,
            refresh_token=refresh_token,
            shipping_address=user.shipping_address,
            phone=user.phone,
            option=user_pb2.SelectOption.REFRESH_TOKEN,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafka.send_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )
        logger.info(f"User verified and email sent back: {user_proto}")


async def handle_delete_user(userid: Union[str, int]):
    userid = int(userid)
    with Session(db.engine) as session:
        user = await crud.get_user_id(session, userid)
        logger.info(f"User with id: {userid} deleted")
        if user:
            session.delete(user)
            session.commit()
            logger.info(f"User with id: {userid } deleted")

        #     user_proto = user_pb2.User(
        #         message="User deleted successfully", option=user_pb2.SelectOption.DELETE
        #     )
        # else:
        #     user_proto = user_pb2.User(
        #         error_message="User not found", http_status_code=404
        #     )
        # serialized_user = user_proto.SerializeToString()
        # await kafka.send_message(settings.KAFKA_TOPIC_USER, serialized_user)
        # logger.info(f"User deleted and confirmation sent back: {user_proto}")


async def process_message(new_msg: user_pb2.User):
    try:
        logger.info(f"Received message: {new_msg}")

        if new_msg.option == user_pb2.SelectOption.REGISTER:
            await handle_register_user(new_msg)
        elif new_msg.option == user_pb2.SelectOption.LOGIN:
            await handle_login(new_msg)
        elif new_msg.option == user_pb2.SelectOption.CURRENT_USER:
            await handle_verify_user(new_msg)
        elif new_msg.option == user_pb2.SelectOption.REFRESH_TOKEN:
            await handle_refresh_token(new_msg)
        elif new_msg.option == user_pb2.SelectOption.DELETE:
            logger.info("Deleting inside the consumer")
            await handle_delete_user(new_msg.user_id)
        else:
            logger.warning(f"Unknown option received: {new_msg.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def start_consuming():
    try:
        consumer = kafka.consume_messages_user(
            settings.KAFKA_TOPIC_USER, settings.KAFKA_CONSUMER_GROUP_ID_FOR_USER
        )
        logger.info("Consumer started")
        async for message in consumer:
            await process_message(message)
    except Exception as e:
        logger.error(f"Error in consumer: {e}")


# async def handle_create_user(new_msg):
#     user = models.User(
#         username=new_msg.username,
#         email=new_msg.email,
#         shipping_address=new_msg.shipping_address,
#         phone=new_msg.phone,
#         password=auth.hash_password(new_msg.password),
#     )
#     with Session(db.engine) as session:
#         session.add(user)
#         session.commit()
#         session.refresh(user)
#         user_proto = user_pb2.User(
#             id=user.id,
#             user_id=str(user.user_id),
#             username=user.username,
#             email=user.email,
#             phone=user.phone,
#             password=user.password,
#             shipping_address=user.shipping_address,
#             option=user_pb2.SelectOption.CREATE,
#         )
#         serialized_user = user_proto.SerializeToString()
#         await kafka.send_message(settings.KAFKA_TOPIC_USER_GET, serialized_user)
#         logger.info(f"User created and sent back: {user_proto}")


# async def handle_read_user(new_msg):
#     with Session(db.engine) as session:
#         user = session.exec(
#             select(models.User).where(models.User.user_id == new_msg.user_id)
#         ).first()
#         if user:
#             user_proto = user_pb2.User(
#                 id=user.id,
#                 user_id=str(user.user_id),
#                 username=user.username,
#                 email=user.email,
#                 password=user.password,
#                 shipping_address=user.shipping_address,
#                 phone=user.phone,
#                 option=user_pb2.SelectOption.READ,
#             )
#         else:
#             user_proto = user_pb2.User(
#                 error_message="User not found", http_status_code=404
#             )
#         serialized_user = user_proto.SerializeToString()
#         await kafka.send_message(settings.KAFKA_TOPIC_USER_GET, serialized_user)
#         logger.info(f"User read and sent back: {user_proto}")


# async def handle_update_user(new_msg):
#     with Session(db.engine) as session:
#         user = session.exec(
#             select(models.User).where(models.User.user_id == new_msg.user_id)
#         ).first()
#         if user:
#             user.username = new_msg.username
#             user.email = new_msg.email
#             user.shipping_address = new_msg.shipping_address
#             user.phone = new_msg.phone
#             if new_msg.password:
#                 user.password = auth.hash_password(new_msg.password)
#             session.add(user)
#             session.commit()
#             session.refresh(user)
#             user_proto = user_pb2.User(
#                 id=user.id,
#                 user_id=str(user.user_id),
#                 username=user.username,
#                 email=user.email,
#                 password=user.password,
#                 shipping_address=user.shipping_address,
#                 phone=user.phone,
#                 option=user_pb2.SelectOption.UPDATE,
#             )
#         else:
#             user_proto = user_pb2.User(
#                 error_message="User not found", http_status_code=404
#             )
#         serialized_user = user_proto.SerializeToString()
#         await kafka.send_message(settings.KAFKA_TOPIC_USER_GET, serialized_user)
#         logger.info(f"User updated and sent back: {user_proto}")


# elif new_msg.option == user_pb2.SelectOption.CREATE:
#     await handle_create_user(new_msg)
# elif new_msg.option == user_pb2.SelectOption.READ:
#     await handle_read_user(new_msg)
# elif new_msg.option == user_pb2.SelectOption.UPDATE:
#     await handle_update_user(new_msg)
