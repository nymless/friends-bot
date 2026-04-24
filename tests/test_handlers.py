import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from friends_bot.database import DBHandler
from friends_bot.enums import GameType
from friends_bot.handlers import start_game, start_loser_game, start_winner_game


@pytest.fixture(autouse=True)
def clear_locks():
    """
    Очистка глобального словаря lock'ов перед каждым тестом.

    Почему это важно:
    chat_locks - это глобальное состояние.
    Без очистки один тест может повлиять на другой
    (например, lock уже будет захвачен или создан).
    """
    from friends_bot.handlers import chat_locks

    chat_locks.clear()


@pytest.mark.asyncio
async def test_start_game_already_run():
    """
    Проверка сценария, когда игра уже была проведена сегодня.

    Ожидаемое поведение:
    - бот не начинает игру
    - сразу сообщает пользователю
    - не обращается к списку игроков
    """

    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    # Симулируем состояние БД:
    # победитель уже есть (возвращается user_id)
    db.is_already_runned.return_value = (12345,)

    await start_game(chat_id=1, game_type=GameType.LOSER, message=message, db=db)

    # Проверяем, что бот корректно сообщил об этом
    message.answer.assert_called_with("Сегодня выбор уже сделан!")

    # Важно: дальнейшая логика не должна выполняться
    db.get_players.assert_not_called()


@pytest.mark.asyncio
async def test_start_game_no_players():
    """
    Проверка сценария, когда нет зарегистрированных игроков.

    Ожидаемое поведение:
    - игра не запускается
    - бот сообщает, что игроков нет
    """

    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    # Игра ещё не проводилась
    db.is_already_runned.return_value = None

    # Но игроков нет
    db.get_players.return_value = []

    await start_game(chat_id=1, game_type=GameType.LOSER, message=message, db=db)

    # Проверяем корректный ответ
    message.answer.assert_called_with("Никто не зарегистрировался!")


@pytest.mark.asyncio
async def test_start_loser_game_success_flow():
    """
    Проверка полного успешного сценария игры (loser).

    Сценарий:
    - игра ещё не проводилась
    - есть хотя бы один игрок
    - бот проводит "анимацию" (последовательность сообщений)
    - затем записывает результат

    Проверяем:
    - количество сообщений
    - финальное сообщение
    - запись результата в БД
    """

    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    db.is_already_runned.return_value = None

    # Один игрок - он гарантированно будет выбран
    db.get_players.return_value = [(999, "Test Name")]

    await start_game(chat_id=1, game_type=GameType.LOSER, message=message, db=db)

    # Проверяем, что отправлена вся последовательность сообщений
    assert message.answer.call_count == 7

    # Собираем отправленные сообщения
    sent_messages = [call.args[0] for call in message.answer.call_args_list]

    # Проверяем финальную строку
    assert "🎉 Сегодня ПИДОР 🌈 дня -  Test Name" in sent_messages[-1]

    # Проверяем запись результата
    db.set_winner.assert_called_once_with(1, 999, GameType.LOSER)


@pytest.mark.asyncio
async def test_start_winner_game_success_flow():
    """
    Проверка полного успешного сценария игры (winner).

    Отличие от предыдущего теста:
    - другой тип игры
    - другой текст финального сообщения

    В остальном сценарий идентичен:
    проверяем корректность всей цепочки действий
    """

    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    db.is_already_runned.return_value = None

    # Два игрока (выбор случайный, но нам важен только текст)
    db.get_players.return_value = [(999, "Test Name"), (999, "Test Name")]

    await start_game(chat_id=1, game_type=GameType.WINNER, message=message, db=db)

    # Проверяем количество сообщений
    assert message.answer.call_count == 7

    # Собираем отправленные сообщения
    sent_messages = [call.args[0] for call in message.answer.call_args_list]

    # Проверяем финальное сообщение
    assert "🎉 Сегодня красавчик дня -  Test Name" in sent_messages[-1]

    # Проверяем запись результата
    db.set_winner.assert_called_once_with(1, 999, GameType.WINNER)


@pytest.mark.asyncio
async def test_start_winner_game_calls_logic():
    """
    Проверка, что handler корректно делегирует выполнение в start_game.

    Мы не тестируем саму логику игры, а проверяем:
    - правильный chat_id
    - правильный GameType
    """

    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    # Подменяем start_game, чтобы не выполнять реальную логику
    with patch(
        "friends_bot.handlers.start_game", new_callable=AsyncMock
    ) as mocked_logic:
        await start_winner_game(message, db)

        # Проверяем корректность вызова
        mocked_logic.assert_called_once_with(
            message.chat.id, GameType.WINNER, message, db
        )


@pytest.mark.asyncio
async def test_start_loser_game_calls_logic():
    """
    Аналогичный тест для loser-игры.

    Проверяем:
    handler должен передать управление в start_game
    с правильным типом игры (GameType.LOSER)
    """

    message = AsyncMock()
    db = MagicMock(spec=DBHandler)

    with patch(
        "friends_bot.handlers.start_game", new_callable=AsyncMock
    ) as mocked_logic:
        await start_loser_game(message, db)

        mocked_logic.assert_called_once_with(
            message.chat.id, GameType.LOSER, message, db
        )


@pytest.mark.asyncio
async def test_start_game_lock_prevents_race():
    """
    Проверка, что при параллельном запуске игры в одном чате
    победитель записывается только один раз.

    Сценарий:
    - Два вызова start_game стартуют "одновременно"
    - Первый выбирает победителя и записывает его
    - Второй должен увидеть, что победитель уже есть, и не вызвать set_winner

    Важно:
    Lock сам по себе не запрещает второй вызов - он сериализует последовательность
    выполнения. Поэтому мы дополнительно симулируем поведение БД через состояние state:
    после первого set_winner состояние меняется.
    """

    message1 = AsyncMock()
    message2 = AsyncMock()

    db = MagicMock(spec=DBHandler)

    # Имитация состояния БД:
    # сначала победителя нет, после записи — появляется
    state = {"has_winner": False}

    def is_already_runned(*args, **kwargs):
        # Возвращаем None, пока победителя нет,
        # и любое значение (как будто найден user_id), если уже есть
        return (1,) if state["has_winner"] else None

    def set_winner(*args, **kwargs):
        # При записи победителя "фиксируем" состояние, как посторонний эффект
        state["has_winner"] = True

    db.is_already_runned.side_effect = is_already_runned
    db.get_players.return_value = [(1, "User")]
    db.set_winner.side_effect = set_winner

    # Запускаем два вызова параллельно
    await asyncio.gather(
        start_game(1, GameType.WINNER, message1, db),
        start_game(1, GameType.WINNER, message2, db),
    )

    # Победитель должен быть записан только один раз
    assert db.set_winner.call_count == 1


@pytest.mark.asyncio
async def test_start_game_lock_serializes_execution():
    """
    Проверка, что Lock действительно сериализует последовательность выполнения.

    Сценарий:
    - Первый вызов start_game проходит полностью
    - Второй начинается только после него
    - И уже видит, что игра была запущена

    Проверка:
    второй вызов не должен доходить до get_players
    """

    message1 = AsyncMock()
    message2 = AsyncMock()

    db = MagicMock(spec=DBHandler)

    # Первый вызов - игры ещё нет
    # Второй вызов - игра уже была (после первого)
    db.is_already_runned.side_effect = [None, (1,)]
    db.get_players.return_value = [(1, "User")]

    db.set_winner = MagicMock()

    # Запускаем два вызова параллельно
    await asyncio.gather(
        start_game(1, GameType.WINNER, message1, db),
        start_game(1, GameType.WINNER, message2, db),
    )

    # get_players должен быть вызван только один раз:
    # второй вызов не дошёл до этой стадии
    assert db.get_players.call_count == 1


@pytest.mark.asyncio
async def test_lock_is_per_chat():
    """
    Проверка, что Lock применяется на уровне chat_id, а не глобально.

    Сценарий:
    - Запускаем игру одновременно в двух разных чатах
    - Они не должны блокировать друг друга

    Проверка:
    оба вызова должны успешно записать победителя
    """

    message1 = AsyncMock()
    message2 = AsyncMock()

    db = MagicMock(spec=DBHandler)

    db.is_already_runned.return_value = None
    db.get_players.return_value = [(1, "User")]

    db.set_winner = MagicMock()

    # Запускаем два вызова в разных чатах параллельно
    await asyncio.gather(
        start_game(1, GameType.WINNER, message1, db),
        start_game(2, GameType.WINNER, message2, db),
    )

    # Оба вызова должны выполниться независимо
    assert db.set_winner.call_count == 2
