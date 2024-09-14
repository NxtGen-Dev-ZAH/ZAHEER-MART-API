# settings.py
from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()


# JWT VARIABLES
SECRET_KEY = config("SECRET_KEY", cast=str)
ALGORITHM = config("ALGORITHM", cast=str)
JWT_EXPIRY_TIME = config("JWT_EXPIRY_TIME", cast=int)


DATABASE_URL = config("DATABASE_URL", cast=Secret)
BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)

KAFKA_TOPIC_PAYMENT = config("KAFKA_TOPIC_PAYMENT", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_PAYMENT = config(
    "KAFKA_CONSUMER_GROUP_ID_FOR_PAYMENT", cast=str
)

KAFKA_TOPIC_GET_FROM_ORDER = config("KAFKA_TOPIC_GET_FROM_ORDER", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_ORDER = config(
    "KAFKA_CONSUMER_GROUP_ID_FOR_ORDER", cast=str
)

KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT = config(
    "KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT", cast=str
)
KAFKA_CONSUMER_GROUP_ID_FOR_RESPONSE_FROM_USER = config(
    "KAFKA_CONSUMER_GROUP_ID_FOR_RESPONSE_FROM_USER", cast=str
)

KAFKA_TOPIC_REQUEST_TO_USER = config("KAFKA_TOPIC_REQUEST_TO_USER", cast=str)
