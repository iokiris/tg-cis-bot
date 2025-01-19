import logging
from aiogram import Bot

API_TOKEN = ''

CHANNEL_ID = '-1234'
CHANNEL_LINK="https://t.me/channel"

CHAT_ID = '-12345'
CHAT_LINK="https://t.me/+chat"

BOT_ID = "cisbot999_bot"


class DatabaseConfig:
    database = "csi_users"
    user = "cessq19"
    password = "dinozavr1"
    host = "localhost"
    port = "5432"

    @staticmethod
    def as_dict():
        return {
            'database': DatabaseConfig.database,
            'user': DatabaseConfig.user,
            'password': DatabaseConfig.password,
            'host': DatabaseConfig.host,
            'port': DatabaseConfig.port
        }


# Logging setup
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
