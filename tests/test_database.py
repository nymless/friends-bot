import pytest

from friends_bot.database import DBHandler
from friends_bot.enums import GameType


@pytest.fixture
def db():
    """
    Создает изолированную SQLite-базу в памяти для каждого теста.

    Почему важно:
    - тесты не влияют друг на друга
    - состояние всегда чистое
    - максимально приближено к реальной БД
    """
    handler = DBHandler(":memory:")
    yield handler
    handler.close()


def test_register_and_update_user(db):
    """
    Проверка идемпотентности поведения регистрации пользователя.

    Сценарий:
    - пользователь регистрируется первый раз
    - затем регистрируется повторно с новыми данными

    Ожидаемое поведение:
    - запись не дублируется (работает PRIMARY KEY + ON CONFLICT)
    - данные обновляются
    """
    # Первая регистрация
    db.register_user(chat_id=1, user_id=10, username="usertest", full_name="Name Test")
    players = db.get_players(chat_id=1)

    assert len(players) == 1
    assert players[0][1] == "Name Test"

    # Повторная регистрация с изменением имени
    db.register_user(chat_id=1, user_id=10, username="testuser", full_name="Test Name")
    players = db.get_players(chat_id=1)

    # Строка не дублируется
    assert len(players) == 1

    # Данные обновились
    assert players[0][1] == "Test Name"


def test_unregister_and_re_register(db):
    """
    Проверка "мягкого удаления" пользователя.

    Сценарий:
    - пользователь регистрируется
    - затем "удаляется" (is_active = 0)
    - затем регистрируется снова

    Ожидаемое поведение:
    - удалённый пользователь не участвует в игре
    - при повторной регистрации снова становится активным
    """

    db.register_user(1, 10, "testuser", "Test Name")

    # Деактивация пользователя
    db.unregister_user(1, 10)

    players = db.get_players(chat_id=1)

    # Пользователь не участвует в игре
    assert len(players) == 0

    # Повторная регистрация (должна активировать обратно)
    db.register_user(1, 10, "testuser", "Test Name")

    players = db.get_players(chat_id=1)

    # Снова активен
    assert len(players) == 1


def test_exclude_today_winner(db):
    """
    Проверка бизнес-правила:
    пользователь, уже участвовавший сегодня (win/lose),
    не должен попадать в выборку для новой игры.

    Сценарий:
    - два пользователя зарегистрированы
    - одному назначаем победу (WINNER)
    - запрашиваем список игроков

    Ожидаемое поведение:
    - пользователь с результатом за сегодня исключается
    """

    db.register_user(1, 10, "testuser1", "Test Name1")
    db.register_user(1, 20, "testuser2", "Test Name2")

    # Назначаем победителя
    db.set_winner(chat_id=1, user_id=20, game_type=GameType.WINNER)

    # Получаем список доступных игроков
    players = db.get_players(chat_id=1)

    # Должен остаться только один
    assert len(players) == 1

    # И это не тот, кто уже выиграл
    assert players[0][0] == 10


def test_chat_isolation(db):
    """
    Проверка изоляции данных по chat_id.

    Сценарий:
    - один и тот же пользователь в двух чатах
    - игра проводится только в одном чате

    Ожидаемое поведение:
    - состояние одного чата не влияет на другой
    - статистика и выбор игроков независимы
    """

    user_id = 777
    chat_one = 1
    chat_two = 2

    # Регистрируем пользователя в двух чатах
    db.register_user(chat_one, user_id, "testuser", "Test Name")
    db.register_user(chat_two, user_id, "testuser", "Test Name")

    # Проводим игру только в первом чате
    db.set_winner(chat_one, user_id, GameType.LOSER)

    # В первом чате игра уже была
    assert db.is_already_runned(chat_one, GameType.LOSER) is not None

    # Во втором — нет
    assert db.is_already_runned(chat_two, GameType.LOSER) is None

    # Проверяем список игроков

    # В первом чате пользователь уже участвовал - исключён
    players_one = db.get_players(chat_one)
    assert len(players_one) == 0

    # Во втором чате он доступен
    players_two = db.get_players(chat_two)
    assert len(players_two) == 1
    assert players_two[0][0] == user_id


def test_unique_index_prevents_two_winners_same_day(db):
    """
    Проверка ограничения UNIQUE INDEX:
    в одном чате не может быть двух победителей в один день.

    Сценарий:
    - два пользователя
    - пытаемся записать победу для обоих в один день

    Ожидаемое поведение:
    - второй INSERT падает с IntegrityError
    """

    db.register_user(1, 10, "user1", "User 1")
    db.register_user(1, 20, "user2", "User 2")

    # Первый победитель - ok
    assert db.set_winner(1, 10, GameType.WINNER) is True

    # Второй должен нарушить UNIQUE INDEX
    assert db.set_winner(1, 20, GameType.WINNER) is False
