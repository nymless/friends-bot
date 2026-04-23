import asyncio
import logging
import random

from aiogram import F, Router, types
from aiogram.filters import Command

from friends_bot.app_types import GameType, GameTypes
from friends_bot.config import ALLOWED_CHAT_ID, ALLOWED_CHAT_TYPES
from friends_bot.database import DBHandler

logger = logging.getLogger(__name__)

router = Router()

# Bot router protection settings
router.message.filter(
    F.chat.type.in_(ALLOWED_CHAT_TYPES),
    F.chat.id == ALLOWED_CHAT_ID,
)


# Bot router handlers
@router.message(Command("reg"))
async def register(message: types.Message, db: DBHandler):
    user = message.from_user

    if not user:
        logger.warning(
            f"Попытка регистрации в чате {message.chat.id} без объекта User. "
            f"Message: {message.text}"
        )
        await message.answer("Ошибка: бот не может зарегистрировать пользователя.")
        return

    db.register_user(
        message.chat.id,
        user.id,
        user.username,
        user.full_name,
    )
    await message.answer("Ты в игре!")


@router.message(Command("delete"))
async def unregister(message: types.Message, db: DBHandler):
    user = message.from_user

    if not user:
        logger.warning(
            f"Попытка снятия регистрации в чате {message.chat.id} без объекта User. "
            f"Message: {message.text}"
        )
        await message.answer("Ошибка: бот не может снять регистрацию пользователя.")
        return

    deleted = db.unregister_user(message.chat.id, user.id)
    if deleted:
        await message.answer("Ты вышел из игры. Но мы всё помним... 😉")


MESSAGES = {
    "loser": [
        "ВНИМАНИЕ 🔥",
        "ФЕДЕРАЛЬНЫЙ 🔍 РОЗЫСК ПИДОРА 🚨",
        "4 - спутник запущен 🚀",
        "3 - сводки Интерпола проверены 🚓",
        "2 - твои друзья опрошены 🙅",
        "1 - твой профиль в соцсетях проанализирован 🙀",
        "🎉 Сегодня ПИДОР 🌈 дня -  ",
    ],
    "winner": [
        "КРУТИМ БАРАБАН",
        "Ищем красавчика в этом чате",
        "Гадаем на бинарных опционах 📊",
        "Анализируем лунный гороскоп 🌖",
        "Лунная призма, дай мне силу! 💫",
        "СЕКТОР ПРИЗ НА БАРАБАНЕ 🎯",
        "🎉 Сегодня красавчик дня -  ",
    ],
}


async def start_game(
    chat_id: int, game_type: GameTypes, message: types.Message, db: DBHandler
):
    already_won = db.is_already_runned(chat_id, game_type)
    if already_won:
        await message.answer("Сегодня выбор уже сделан!")
        return

    players = db.get_players(chat_id)
    if not players:
        await message.answer("Никто не зарегистрировался!")
        return

    user_id, full_name = random.choice(players)
    winner_message = MESSAGES[game_type]
    winner_message[-1] += full_name

    for step in winner_message:
        await message.answer(step)
        await asyncio.sleep(1.5)

    db.set_winner(chat_id, user_id, game_type)


@router.message(Command("run"))
async def start_winner_game(message: types.Message, db: DBHandler):
    await start_game(message.chat.id, GameType.WINNER, message, db)


@router.message(Command("pidor"))
async def start_loser_game(message: types.Message, db: DBHandler):
    await start_game(message.chat.id, GameType.LOSER, message, db)


async def show_statistics(message: types.Message, db: DBHandler, game_type: GameTypes):
    stats = db.get_statistics(message.chat.id, game_type)

    if not stats:
        await message.answer("Статистика пока пуста. Сначала сыграйте в игру!")
        return

    if game_type == GameType.WINNER:
        title = "🎉 Результаты Красавчик Дня\n"
    else:
        title = "Результаты 🌈ПИДОР Дня\n"

    # Forming a list of the following type: 1) Имя - N раз(а)
    lines = []
    for i, (name, count) in enumerate(stats, 1):
        lines.append(f"{i}) {name} — {count} раз(а)")

    response = title + "\n".join(lines)
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("stats"))
async def show_winner_statistics(message: types.Message, db: DBHandler):
    await show_statistics(message, db, GameType.WINNER)


@router.message(Command("pidorstats"))
async def show_loser_statistics(message: types.Message, db: DBHandler):
    await show_statistics(message, db, GameType.LOSER)
