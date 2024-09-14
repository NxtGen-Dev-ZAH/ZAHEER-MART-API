# settings.py
from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

FROM_EMAIL = config("FROM_EMAIL", cast=str)
FROM_EMAIL_APP_PASSWORD = config("FROM_EMAIL_APP_PASSWORD", cast=str)
DATABASE_URL = config("DATABASE_URL", cast=Secret)



BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)

KAFKA_TOPIC_USER = config("KAFKA_TOPIC_TO_CONSUME_NEW_USER", cast=str)
KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_NEW_USER = config("KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_NEW_USER", cast=str)


KAFKA_TOPIC_ORDER= config("KAFKA_TOPIC_TO_CONSUME_ORDER_CREATED", cast=str)
KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_ORDER_CREATED = config("KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_ORDER_CREATED", cast=str)

KAFKA_TOPIC_PAYMENT= config("KAFKA_TOPIC_TO_CONSUME_PAYMENT_DONE", cast=str)
KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_PAYMENT_DONE = config("KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_PAYMENT_DONE", cast=str)
