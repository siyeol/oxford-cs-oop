from collections.abc import Callable
from enum import Enum, auto
from typing import Final, Self


class ClanColor(Enum):
    CROCODILE = auto()
    TURTLE = auto()
    FROG = auto()
    SALAMANDER = auto()


class Resource(Enum):
    GOLD = auto()
    MANA = auto()
    FISH = auto()


class Phase(Enum):
    DRAFT = auto()
    PLACEMENT = auto()
    TURNS = auto()
    OVER = auto()


class SpaceKind(Enum):
    WATER = auto()
    SPIRIT = auto()
    TEMPLE = auto()


class ActionKind(Enum):
    FISH = auto()
    BUILD = auto()
    SAIL = auto()
    TRADE = auto()
    IMPROVE_SAILING = auto()
    CELEBRATE = auto()
    ADD_SPIRIT = auto()
    PASS = auto()


class GuideKind(Enum):
    LEADER = auto()
    SAILOR = auto()
    FISHERMAN = auto()
    MONK = auto()
    STORYTELLER = auto()
    BUILDER = auto()
    WARRIOR = auto()
    MERCHANT = auto()
    ARTIST = auto()
    WISEMAN = auto()


type SpaceId = int
type IslandId = int
type BoatId = int
type ScoreEvent = tuple[ClanColor, int]


class GameError(Exception):
    pass


class IllegalSetup(GameError):
    pass


class IllegalMove(GameError):
    pass


class WrongPhase(IllegalMove):
    pass


class NotYourTurn(IllegalMove):
    pass


class InsufficientResources(IllegalMove):
    pass


class IllegalPlacement(IllegalMove):
    pass


class Observable[T]:
    __slots__ = ("_subscribers",)

    _subscribers: list[Callable[[T], None]]

    def __new__(cls) -> Self:
        self = super().__new__(cls)
        self._subscribers = []
        return self

    def subscribe(self, callback: Callable[[T], None]) -> None:
        self._subscribers.append(callback)

    def _notify(self, event: T) -> None:
        for callback in tuple(self._subscribers):
            callback(event)


ROUNDS: Final[int] = 4
STARTING_GOLD: Final[int] = 20
STARTING_MANA: Final[int] = 1
STARTING_FISH: Final[int] = 3
BASE_WORKERS: Final[int] = 3
BOATS_PER_CLAN: Final[int] = 3
STARTING_SETTLEMENTS: Final[int] = 3
NEUTRAL_WORKERS: Final[int] = 8
MAX_FISH_STACK: Final[int] = 3
SPIRIT_BUILD_COST: Final[int] = 3
MANA_PER_NEUTRAL: Final[int] = 2
WORKER_TO_MANA: Final[int] = 1
GUIDES_IN_OFFER: Final[int] = 7
SCORE_CARDS_IN_PLAY: Final[int] = 2
TRADE_REWARD: Final[tuple[int, ...]] = (4, 3, 2)
TOTEM_TRADE_BONUS: Final[int] = 1
CELEBRATE_TOTEM_BONUS: Final[int] = 3
SAILING_VP: Final[tuple[int, ...]] = (1, 2, 4, 6, 9, 12)
SAIL_MAP_BONUS_MIN_PLAYERS: Final[int] = 3
SAIL_MAP_BONUS: Final[int] = 2
INCOME_MANA: Final[int] = 1
INCOME_GOLD_PER_SETTLEMENT: Final[int] = 2
FISH_VP_DIVISOR: Final[int] = 1
GOLD_VP_DIVISOR: Final[int] = 10
TEMPLE_NEIGHBOUR_VP: Final[int] = 5
ISLAND_LEAD_VP: Final[int] = 3
SOLE_SETTLEMENT_VP: Final[int] = 5
SIZE_ISLAND_VP: Final[int] = 4
