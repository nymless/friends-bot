import pytest

from friends_bot.app_types import GameType
from friends_bot.database import DBHandler


@pytest.fixture
def db():
    """Создает чистую базу в памяти для каждого теста"""
    handler = DBHandler(":memory:")
    yield handler
    handler.close()


def test_register_and_update_user(db):
    # 1. Первая регистрация
    db.register_user(chat_id=1, user_id=10, username="usertest", full_name="Name Test")
    players = db.get_players(chat_id=1)

    assert len(players) == 1
    assert players[0][1] == "Name Test"

    # 2. Обновление (смена имени)
    db.register_user(chat_id=1, user_id=10, username="testuser", full_name="Test Name")
    players = db.get_players(chat_id=1)

    assert len(players) == 1  # Строка всё еще одна (сработал ON CONFLICT)
    assert players[0][1] == "Test Name"  # Имя обновилось


def test_unregister_and_re_register(db):
    db.register_user(1, 10, "testuser", "Test Name")

    # Удаляем (is_active = 0)
    db.unregister_user(1, 10)
    players = db.get_players(chat_id=1)
    assert len(players) == 0  # В выборку для игры не попал

    # Регистрируем снова
    db.register_user(1, 10, "testuser", "Test Name")
    players = db.get_players(chat_id=1)
    assert len(players) == 1  # Снова активен


def test_exclude_today_winner(db):
    db.register_user(1, 10, "testuser1", "Test Name1")
    db.register_user(1, 20, "testuser2", "Test Name2")

    # Помечаем второго как красавчика (winner)
    db.set_winner(chat_id=1, user_id=20, game_type=GameType.WINNER)

    # Пытаемся получить игроков для игры в лузера
    # Красавчик должен быть исключен
    players = db.get_players(chat_id=1)

    assert len(players) == 1
    assert players[0][0] == 10  # Остался только первый юзер


def test_chat_isolation(db):
    user_id = 777
    chat_one = 1
    chat_two = 2

    # 1. Регистрируем одного и того же юзера в двух разных чатах
    db.register_user(chat_one, user_id, "testuser", "Test Name")
    db.register_user(chat_two, user_id, "testuser", "Test Name")

    # 2. Проводим игру в первом чате
    db.set_winner(chat_one, user_id, GameType.LOSER)

    # 3. ПРОВЕРКА: В первом чате игра должна быть "уже запущена"
    assert db.is_already_runned(chat_one, GameType.LOSER) is not None

    # 4. ПРОВЕРКА: Во втором чате игра НЕ должна быть запущена
    # Хотя юзер тот же, запись в stats привязана к chat_id
    assert db.is_already_runned(chat_two, GameType.LOSER) is None

    # 5. ПРОВЕРКА: Списки игроков тоже должны быть независимы
    # В первом чате (где уже выбрали лузера) список игроков для лузера должен быть пуст
    players_one = db.get_players(chat_one)
    assert len(players_one) == 0

    # Во втором чате юзер всё еще должен быть доступен для выбора
    players_two = db.get_players(chat_two)
    assert len(players_two) == 1
    assert players_two[0][0] == user_id
