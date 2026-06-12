from abc import ABC, abstractmethod
from typing import Final, Protocol

from .board import Swamp
from .core import (
    ClanColor,
    ISLAND_LEAD_VP,
    SIZE_ISLAND_VP,
    SOLE_SETTLEMENT_VP,
    SpaceId,
    SpaceKind,
    TEMPLE_NEIGHBOUR_VP,
)
from .structures import UnionFind


def islands_led(swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]) -> int:
    total = 0
    for island in swamp.islands():
        mine = island.settlements(color)
        if mine > 0 and mine == max(island.settlements(c) for c in colors):
            total += 1
    return total


class ScoreCardView(Protocol):
    @property
    def card_id(self) -> int: ...
    @property
    def name(self) -> str: ...


class ScoreCard(ABC):
    __slots__ = ()

    @property
    @abstractmethod
    def card_id(self) -> int: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int: ...


class LargestGroupCard(ScoreCard):
    __slots__ = ()

    @property
    def card_id(self) -> int:
        return 0

    @property
    def name(self) -> str:
        return "squared size of the largest connected group of settlements"

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        cells = swamp.settlements_of(color)
        union: UnionFind[SpaceId] = UnionFind()
        for sid in cells:
            union.add(sid)
        present = set(cells)
        for sid in cells:
            for neighbour in swamp.neighbours(sid):
                if neighbour in present:
                    union.union(sid, neighbour)
        largest = max((len(group) for group in union.components()), default=0)
        return largest * largest


class TempleAdjacentCard(ScoreCard):
    __slots__ = ()

    @property
    def card_id(self) -> int:
        return 1

    @property
    def name(self) -> str:
        return "five points per settlement next to a temple space"

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        count = 0
        for sid in swamp.settlements_of(color):
            if any(
                swamp.space(n).kind is SpaceKind.TEMPLE for n in swamp.neighbours(sid)
            ):
                count += 1
        return count * TEMPLE_NEIGHBOUR_VP


class IslandLeadCard(ScoreCard):
    __slots__ = ()

    @property
    def card_id(self) -> int:
        return 2

    @property
    def name(self) -> str:
        return "three points per island where you lead in settlements"

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        return ISLAND_LEAD_VP * islands_led(swamp, color, colors)


class SoleSettlementCard(ScoreCard):
    __slots__ = ()

    @property
    def card_id(self) -> int:
        return 3

    @property
    def name(self) -> str:
        return "five points per island where you have exactly one settlement"

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        total = 0
        for island in swamp.islands():
            if island.settlements(color) == 1:
                total += SOLE_SETTLEMENT_VP
        return total


class LargestIslandCard(ScoreCard):
    __slots__ = ()

    @property
    def card_id(self) -> int:
        return 4

    @property
    def name(self) -> str:
        return "four points per settlement on the largest island"

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        islands = swamp.islands()
        if not islands:
            return 0
        target = max(island.size for island in islands)
        return SIZE_ISLAND_VP * sum(
            island.settlements(color) for island in islands if island.size == target
        )


class SmallestIslandCard(ScoreCard):
    __slots__ = ()

    @property
    def card_id(self) -> int:
        return 5

    @property
    def name(self) -> str:
        return "four points per settlement on the smallest island"

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        islands = swamp.islands()
        if not islands:
            return 0
        target = min(island.size for island in islands)
        return SIZE_ISLAND_VP * sum(
            island.settlements(color) for island in islands if island.size == target
        )


SCORE_CARDS: Final[tuple[ScoreCard, ...]] = (
    LargestGroupCard(),
    TempleAdjacentCard(),
    IslandLeadCard(),
    SoleSettlementCard(),
    LargestIslandCard(),
    SmallestIslandCard(),
)
