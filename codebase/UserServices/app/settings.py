from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")

except FileNotFoundError:
    config = Config()

DATABASE_URL = config("DATABASE_URL", cast=Secret)
BOOTSTRAP_SERVER = config("KAFKA_SERVER", cast=str)
KAFKA_TOPIC_USER = config("KAFKA_TOPIC_USER", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_USER = config("KAFKA_CONSUMER_GROUP_ID_FOR_USER", cast=str)

SECRET_KEY = config("SECRET_KEY", cast=str)
ALGORITHM = config("ALGORITHM", cast=str)
JWT_EXPIRY_TIME = config("JWT_EXPIRY_TIME", cast=int)

KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER = config(
    "KAFKA_TOPIC_RESPONSE_FROM_USER_TO_ORDER", cast=str
)
KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT = config(
    "KAFKA_TOPIC_RESPONSE_FROM_USER_TO_PAYMENT", cast=str
)
