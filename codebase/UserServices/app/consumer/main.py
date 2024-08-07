from sqlmodel import select, Session
from app import settings, user_pb2, db, kafkafile, auth, models
from aiokafka import AIOKafkaConsumer
from datetime import timedelta
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_register_user(new_msg):
    user = auth.check_user_in_db(new_msg.username, new_msg.email)
    if user:
        user_proto = user_pb2.User(
            error_message="User with these credentials already exists in database",
            http_status_code=409,
        )
        serialized_user = user_proto.SerializeToString()
        await kafkafile.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)
    else:
        user = models.UserCreate(
            username=new_msg.username,
            email=new_msg.email,
            password=auth.hash_password(new_msg.password),
        )
        with Session(db.engine) as session:
            session.add(user)
            session.commit()
            logger.info(f"User added to database: {user}")
            session.refresh(user)
            user_proto = user_pb2.User(
                id=user.id,
                user_id=str(user.user_id),
                username=user.username,
                email=user.email,
                password=user.password,
                shipping_address=user.shipping_address,
                phone=user.phone,
                option=user_pb2.SelectOption.REGISTER,
            )
            serialized_user = user_proto.SerializeToString()
            await kafkafile.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)
            logger.info(f"User added to database and sent back: {user_proto}")


async def handle_login(new_msg):
    user = auth.check_user_in_db(new_msg.username, new_msg.password)
    if user:
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
            serialized_user = user_proto.SerializeToString()
            if new_msg.service == user_pb2.SelectService.PAYMENT:
                await kafkafile.produce_message(
                    settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
                )
            elif new_msg.service == user_pb2.SelectService.ORDER:
                await kafkafile.produce_message(
                    settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
                )
            logger.info(f"User logged in and sent back: {user_proto}")
        else:
            user_proto = user_pb2.User(
                error_message="Password is incorrect", http_status_code=401
            )
            serialized_user = user_proto.SerializeToString()
            if new_msg.service == user_pb2.SelectService.PAYMENT:
                await kafkafile.produce_message(
                    settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
                )
            elif new_msg.service == user_pb2.SelectService.ORDER:
                await kafkafile.produce_message(
                    settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
                )
    else:
        user_proto = user_pb2.User(
            error_message=f"{new_msg.username} is not registered in database",
            http_status_code=404,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )


async def handle_verify_user(new_msg):
    logger.info(
        f"Username we get at consumer on user service to verify it: {new_msg.username}"
    )
    user = auth.check_user_in_db(new_msg.username, new_msg.email)
    logger.info(f"detail of user after checking it from database: {user}")
    if not user:
        user_proto = user_pb2.User(
            error_message="User with these credentials do not exist in database",
            http_status_code=404,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )
    else:
        user_proto = user_pb2.User(
            id=user.id,
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
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )
        logger.info(f"User verified and username sent back: {user_proto}")


async def handle_refresh_token(new_msg):
    user = auth.check_user_in_db(new_msg.username, new_msg.email)
    if not user:
        user_proto = user_pb2.User(
            error_message="User with these credentials do not exist in database",
            http_status_code=404,
        )
        serialized_user = user_proto.SerializeToString()
        if new_msg.service == user_pb2.SelectService.PAYMENT:
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafkafile.produce_message(
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
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT, serialized_user
            )
        elif new_msg.service == user_pb2.SelectService.ORDER:
            await kafkafile.produce_message(
                settings.KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER, serialized_user
            )
        logger.info(f"User verified and email sent back: {user_proto}")


async def handle_create_user(new_msg):
    user = models.User(
        username=new_msg.username,
        email=new_msg.email,
        shipping_address=new_msg.shipping_address,
        phone=new_msg.phone,
        password=auth.hash_password(new_msg.password),
    )
    with Session(db.engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        user_proto = user_pb2.User(
            id=user.id,
            user_id=str(user.user_id),
            username=user.username,
            email=user.email,
            phone=user.phone,
            password=user.password,
            shipping_address=user.shipping_address,
            option=user_pb2.SelectOption.CREATE,
        )
        serialized_user = user_proto.SerializeToString()
        await kafkafile.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)
        logger.info(f"User created and sent back: {user_proto}")


async def handle_read_user(new_msg):
    with Session(db.engine) as session:
        user = session.exec(
            select(models.User).where(models.User.user_id == new_msg.user_id)
        ).first()
        if user:
            user_proto = user_pb2.User(
                id=user.id,
                user_id=str(user.user_id),
                username=user.username,
                email=user.email,
                password=user.password,
                shipping_address=user.shipping_address,
                phone=user.phone,
                option=user_pb2.SelectOption.READ,
            )
        else:
            user_proto = user_pb2.User(
                error_message="User not found", http_status_code=404
            )
        serialized_user = user_proto.SerializeToString()
        await kafkafile.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)
        logger.info(f"User read and sent back: {user_proto}")


async def handle_update_user(new_msg):
    with Session(db.engine) as session:
        user = session.exec(
            select(models.User).where(models.User.user_id == new_msg.user_id)
        ).first()
        if user:
            user.username = new_msg.username
            user.email = new_msg.email
            user.shipping_address = new_msg.shipping_address
            user.phone = new_msg.phone
            if new_msg.password:
                user.password = auth.hash_password(new_msg.password)
            session.add(user)
            session.commit()
            session.refresh(user)
            user_proto = user_pb2.User(
                id=user.id,
                user_id=str(user.user_id),
                username=user.username,
                email=user.email,
                password=user.password,
                shipping_address=user.shipping_address,
                phone=user.phone,
                option=user_pb2.SelectOption.UPDATE,
            )
        else:
            user_proto = user_pb2.User(
                error_message="User not found", http_status_code=404
            )
        serialized_user = user_proto.SerializeToString()
        await kafkafile.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)
        logger.info(f"User updated and sent back: {user_proto}")


async def handle_delete_user(new_msg):
    with Session(db.engine) as session:
        user = session.exec(
            select(models.User).where(models.User.user_id == new_msg.user_id)
        ).first()
        if user:
            session.delete(user)
            session.commit()
            user_proto = user_pb2.User(
                message="User deleted successfully", option=user_pb2.SelectOption.DELETE
            )
        else:
            user_proto = user_pb2.User(
                error_message="User not found", http_status_code=404
            )
        serialized_user = user_proto.SerializeToString()
        await kafkafile.produce_message(settings.KAFKA_TOPIC_GET, serialized_user)
        logger.info(f"User deleted and confirmation sent back: {user_proto}")


async def consume_message_request():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC,
        bootstrap_servers=settings.BOOTSTRAP_SERVER,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID_FOR_USER,
        auto_offset_reset="earliest",
    )
    await kafkafile.retry_async(consumer.start)
    try:
        async for msg in consumer:
            new_msg = user_pb2.User()
            new_msg.ParseFromString(msg.value)
            logger.info(f"Received message: {new_msg}")

            if new_msg.option == user_pb2.SelectOption.REGISTER:
                await handle_register_user(new_msg)
            elif new_msg.option == user_pb2.SelectOption.LOGIN:
                await handle_login(new_msg)
            elif new_msg.option == user_pb2.SelectOption.CURRENT_USER:
                await handle_verify_user(new_msg)
            elif new_msg.option == user_pb2.SelectOption.REFRESH_TOKEN:
                await handle_refresh_token(new_msg)
            elif new_msg.option == user_pb2.SelectOption.CREATE:
                await handle_create_user(new_msg)
            elif new_msg.option == user_pb2.SelectOption.READ:
                await handle_read_user(new_msg)
            elif new_msg.option == user_pb2.SelectOption.UPDATE:
                await handle_update_user(new_msg)
            elif new_msg.option == user_pb2.SelectOption.DELETE:
                await handle_delete_user(new_msg)
            else:
                logger.warning(f"Unknown option received: {new_msg.option}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
    finally:
        await consumer.stop()
