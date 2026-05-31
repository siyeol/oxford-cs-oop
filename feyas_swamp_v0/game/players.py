from typing import Protocol, Self

from .board import TempleTile
from .core import (
    BASE_WORKERS,
    BoatId,
    ClanColor,
    InsufficientResources,
    NEUTRAL_WORKERS,
    Resource,
    SAILING_VP,
    STARTING_FISH,
    STARTING_GOLD,
    STARTING_MANA,
)
from .guides import GuideCard, GuideView
from .structures import Bag

type WalletState = tuple[int, int, int]
type PlayerState = tuple[
    int,
    WalletState,
    int,
    int,
    int,
    int,
    GuideCard | None,
    GuideCard | None,
    bool,
    tuple[TempleTile, ...],
]


class Wallet:
    _bag: Bag[Resource]

    def __new__(cls) -> Self:
        self = super().__new__(cls)
        self._bag = Bag()
        return self

    @property
    def gold(self) -> int:
        return self._bag[Resource.GOLD]

    @property
    def mana(self) -> int:
        return self._bag[Resource.MANA]

    @property
    def fish(self) -> int:
        return self._bag[Resource.FISH]

    def amount(self, resource: Resource) -> int:
        return self._bag[resource]

    def _add(self, resource: Resource, amount: int) -> None:
        self._bag.add(resource, amount)

    def _spend(self, resource: Resource, amount: int) -> None:
        if self._bag[resource] < amount:
            raise InsufficientResources(f"need {amount} {resource.name}")
        self._bag.remove(resource, amount)

    def _capture(self) -> WalletState:
        return self.gold, self.mana, self.fish

    def _restore(self, state: WalletState) -> None:
        fresh: Bag[Resource] = Bag()
        if state[0] > 0:
            fresh.add(Resource.GOLD, state[0])
        if state[1] > 0:
            fresh.add(Resource.MANA, state[1])
        if state[2] > 0:
            fresh.add(Resource.FISH, state[2])
        self._bag = fresh


class Bank:
    _neutral_available: int

    def __new__(cls) -> Self:
        self = super().__new__(cls)
        self._neutral_available = NEUTRAL_WORKERS
        return self

    @property
    def neutral_available(self) -> int:
        return self._neutral_available

    def _take_neutral(self, count: int) -> int:
        taken = min(count, self._neutral_available)
        self._neutral_available -= taken
        return taken

    def _return_neutral(self, count: int) -> None:
        self._neutral_available = min(NEUTRAL_WORKERS, self._neutral_available + count)

    def _capture(self) -> int:
        return self._neutral_available

    def _restore(self, state: int) -> None:
        self._neutral_available = state


class PlayerView(Protocol):
    @property
    def color(self) -> ClanColor: ...
    @property
    def score(self) -> int: ...
    @property
    def gold(self) -> int: ...
    @property
    def mana(self) -> int: ...
    @property
    def fish(self) -> int: ...
    @property
    def workers_available(self) -> int: ...
    @property
    def neutral_available(self) -> int: ...
    @property
    def sailing_value(self) -> int: ...
    @property
    def guide(self) -> GuideView | None: ...
    @property
    def passed(self) -> bool: ...
    @property
    def temple_count(self) -> int: ...
    @property
    def boats(self) -> tuple[BoatId, ...]: ...


class Player:
    _color: ClanColor
    _wallet: Wallet
    _score: int
    _workers: int
    _neutral: int
    _neutral_taken: int
    _sailing: int
    _boats: tuple[BoatId, ...]
    _guide: GuideCard | None
    _next_guide: GuideCard | None
    _passed: bool
    _temples: list[TempleTile]

    def __new__(cls, color: ClanColor, boats: tuple[BoatId, ...]) -> Self:
        self = super().__new__(cls)
        self._color = color
        self._wallet = Wallet()
        self._wallet._add(Resource.GOLD, STARTING_GOLD)
        self._wallet._add(Resource.MANA, STARTING_MANA)
        self._wallet._add(Resource.FISH, STARTING_FISH)
        self._score = 0
        self._workers = BASE_WORKERS
        self._neutral = 0
        self._neutral_taken = 0
        self._sailing = 0
        self._boats = boats
        self._guide = None
        self._next_guide = None
        self._passed = False
        self._temples = []
        return self

    @property
    def color(self) -> ClanColor:
        return self._color

    @property
    def score(self) -> int:
        return self._score

    @property
    def gold(self) -> int:
        return self._wallet.gold

    @property
    def mana(self) -> int:
        return self._wallet.mana

    @property
    def fish(self) -> int:
        return self._wallet.fish

    @property
    def workers_available(self) -> int:
        return self._workers + self._neutral

    @property
    def neutral_available(self) -> int:
        return self._neutral

    @property
    def sailing_value(self) -> int:
        return self._sailing

    @property
    def guide(self) -> GuideCard | None:
        return self._guide

    @property
    def next_guide(self) -> GuideCard | None:
        return self._next_guide

    @property
    def passed(self) -> bool:
        return self._passed

    @property
    def temple_count(self) -> int:
        return len(self._temples)

    @property
    def boats(self) -> tuple[BoatId, ...]:
        return self._boats

    def amount(self, resource: Resource) -> int:
        return self._wallet.amount(resource)

    def _award(self, points: int) -> None:
        self._score += points

    def _gain(self, resource: Resource, amount: int) -> None:
        self._wallet._add(resource, amount)

    def _spend(self, resource: Resource, amount: int) -> None:
        self._wallet._spend(resource, amount)

    def _add_neutral(self, count: int) -> None:
        self._neutral += count
        self._neutral_taken += count

    def _use_worker(self) -> None:
        if self._workers > 0:
            self._workers -= 1
        elif self._neutral > 0:
            self._neutral -= 1
        else:
            raise InsufficientResources("no workers available")

    def _advance_sailing(self) -> int:
        if self._sailing >= len(SAILING_VP):
            return 0
        points = SAILING_VP[self._sailing]
        self._sailing += 1
        return points

    def _add_temple(self, tile: TempleTile) -> None:
        self._temples.append(tile)

    def has_temple_type(self, type_id: int) -> bool:
        return any(tile.type_id == type_id for tile in self._temples)

    def _set_guide(self, card: GuideCard) -> None:
        self._guide = card

    def _set_next_guide(self, card: GuideCard) -> None:
        self._next_guide = card

    def _promote_guide(self) -> None:
        if self._next_guide is not None:
            self._guide = self._next_guide
            self._next_guide = None

    def _pass(self) -> None:
        self._passed = True

    def _reset_for_round(self) -> int:
        returned = self._neutral_taken
        self._workers = BASE_WORKERS
        self._neutral = 0
        self._neutral_taken = 0
        self._passed = False
        return returned

    def _capture(self) -> PlayerState:
        return (
            self._score,
            self._wallet._capture(),
            self._workers,
            self._neutral,
            self._neutral_taken,
            self._sailing,
            self._guide,
            self._next_guide,
            self._passed,
            tuple(self._temples),
        )

    def _restore(self, state: PlayerState) -> None:
        self._score = state[0]
        self._wallet._restore(state[1])
        self._workers = state[2]
        self._neutral = state[3]
        self._neutral_taken = state[4]
        self._sailing = state[5]
        self._guide = state[6]
        self._next_guide = state[7]
        self._passed = state[8]
        self._temples = list(state[9])
