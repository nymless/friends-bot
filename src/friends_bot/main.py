import asyncio
import logging
from os import getenv

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from friends_bot.database import DBHandler
from friends_bot.handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():

    load_dotenv()
    token = getenv("BOT_TOKEN")
    db_path = getenv("DB_PATH")
    if not (token and db_path):
        logger.error("Отсутствуеют .env файл или определены не все локальные переменные.")
        return

    bot = Bot(token=token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    db_handler = DBHandler(db_path)

    await dispatcher.start_polling(bot, db=db_handler)


if __name__ == "__main__":
    asyncio.run(main())
