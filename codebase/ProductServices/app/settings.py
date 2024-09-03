# settings.py

from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

DATABASE_URL = config("DATABASE_URL", cast=Secret)
BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)
KAFKA_TOPIC_PRODUCT = config("KAFKA_TOPIC_PRODUCT", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT = config(
    "KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT", cast=str
)
KAFKA_TOPIC_STOCK_LEVEL_CHECK = config("KAFKA_TOPIC_STOCK_LEVEL_CHECK", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_STOCK_LEVEL_CHECK = config(
    "KAFKA_CONSUMER_GROUP_ID_FOR_STOCK_LEVEL_CHECK", cast=str
)
