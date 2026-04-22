from typing import Final, Literal

type GameTypes = Literal["winner", "loser"]


class GameType:
    WINNER: Final = "winner"
    LOSER: Final = "loser"


class DateCol:
    LAST_WIN: Final = "last_win"
    LAST_LOSE: Final = "last_lose"


class CountCol:
    WIN_COUNT: Final = "win_count"
    LOSE_COUNT: Final = "lose_count"
