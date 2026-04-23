from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from friends_bot.app_types import GameType
from friends_bot.database import DBHandler
from friends_bot.handlers import start_game, start_loser_game, start_winner_game


@pytest.mark.asyncio
async def test_start_game_already_run():
    """Проверка случая, когда игра сегодня уже запускалась"""
    # Создаем мок сообщения
    message = AsyncMock()
    # Создаем мок базы данных
    db = MagicMock(spec=DBHandler)

    # Настраиваем мок так, будто выбор уже сделан
    db.is_already_runned.return_value = (12345,)  # Имитируем возврат ID победителя

    await start_game(chat_id=1, game_type="loser", message=message, db=db)

    # Проверяем, что бот ответил нужной фразой
    message.answer.assert_called_with("Сегодня выбор уже сделан!")
    # Проверяем, что поиск игроков даже не начинался
    db.get_players.assert_not_called()


@pytest.mark.asyncio
async def test_start_game_no_players():
    """Проверка случая, когда в базе нет игроков"""
    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    db.is_already_runned.return_value = None
    db.get_players.return_value = []  # Пустой список игроков

    await start_game(chat_id=1, game_type="loser", message=message, db=db)

    message.answer.assert_called_with("Никто не зарегистрировался!")


@pytest.mark.asyncio
async def test_start_loser_game_success_flow():
    """Проверка успешного цикла игры в пидора"""
    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    db.is_already_runned.return_value = None
    # Имитируем одного игрока
    db.get_players.return_value = [(999, "Test Name")]

    await start_game(chat_id=1, game_type="loser", message=message, db=db)

    # Проверяем, что бот отправил сообщения (включая шаги анимации и финал)
    # Всего в winner_message 7 строк. Проверим вызов последней.
    assert message.answer.call_count == 7

    # Извлекаем тексты всех ответов
    sent_messages = [call.args[0] for call in message.answer.call_args_list]

    # Проверяем последнюю фразу
    assert "🎉 Сегодня ПИДОР 🌈 дня -  Test Name" in sent_messages[-1]

    # Проверяем, что победитель был записан в базу
    db.set_winner.assert_called_once_with(1, 999, "loser")


@pytest.mark.asyncio
async def test_start_winner_game_success_flow():
    """Проверка успешного цикла игры в красавчика"""
    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    db.is_already_runned.return_value = None
    # Имитируем два игрока
    db.get_players.return_value = [(999, "Test Name"), (999, "Test Name")]

    await start_game(chat_id=1, game_type="winner", message=message, db=db)

    # Проверяем, что бот отправил сообщения (включая шаги анимации и финал)
    # Всего в winner_message 7 строк. Проверим вызов последней.
    assert message.answer.call_count == 7

    # Извлекаем тексты всех ответов
    sent_messages = [call.args[0] for call in message.answer.call_args_list]

    # Проверяем последнюю фразу
    assert "🎉 Сегодня красавчик дня -  Test Name" in sent_messages[-1]

    # Проверяем, что победитель был записан в базу
    db.set_winner.assert_called_once_with(1, 999, "winner")


@pytest.mark.asyncio
async def test_start_winner_game_calls_logic():
    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    # Мокаем саму функцию start_game
    with patch(
        "friends_bot.handlers.start_game", new_callable=AsyncMock
    ) as mocked_logic:
        await start_winner_game(message, db)

        # Проверяем, что логика вызвана с правильным типом игры
        mocked_logic.assert_called_once_with(
            message.chat.id, GameType.WINNER, message, db
        )


@pytest.mark.asyncio
async def test_start_loser_game_calls_logic():
    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    with patch(
        "friends_bot.handlers.start_game", new_callable=AsyncMock
    ) as mocked_logic:
        await start_loser_game(message, db)

        mocked_logic.assert_called_once_with(
            message.chat.id, GameType.LOSER, message, db
        )
