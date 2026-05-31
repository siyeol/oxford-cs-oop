from abc import ABC, abstractmethod
from typing import Final

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


class ScoreCard(ABC):
    @property
    @abstractmethod
    def card_id(self) -> int: ...

    @abstractmethod
    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int: ...


class LargestGroupCard(ScoreCard):
    @property
    def card_id(self) -> int:
        return 0

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
    @property
    def card_id(self) -> int:
        return 1

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
    @property
    def card_id(self) -> int:
        return 2

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        total = 0
        for island in swamp.islands():
            counts = [swamp.settlements_in(island, c) for c in colors]
            mine = swamp.settlements_in(island, color)
            if mine > 0 and mine == max(counts):
                total += ISLAND_LEAD_VP
        return total


class SoleSettlementCard(ScoreCard):
    @property
    def card_id(self) -> int:
        return 3

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        total = 0
        for island in swamp.islands():
            if swamp.settlements_in(island, color) == 1:
                total += SOLE_SETTLEMENT_VP
        return total


class LargestIslandCard(ScoreCard):
    @property
    def card_id(self) -> int:
        return 4

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        islands = swamp.islands()
        if not islands:
            return 0
        target = max(len(island) for island in islands)
        return SIZE_ISLAND_VP * sum(
            swamp.settlements_in(island, color)
            for island in islands
            if len(island) == target
        )


class SmallestIslandCard(ScoreCard):
    @property
    def card_id(self) -> int:
        return 5

    def score(
        self, swamp: Swamp, color: ClanColor, colors: tuple[ClanColor, ...]
    ) -> int:
        islands = swamp.islands()
        if not islands:
            return 0
        target = min(len(island) for island in islands)
        return SIZE_ISLAND_VP * sum(
            swamp.settlements_in(island, color)
            for island in islands
            if len(island) == target
        )


SCORE_CARDS: Final[tuple[ScoreCard, ...]] = (
    LargestGroupCard(),
    TempleAdjacentCard(),
    IslandLeadCard(),
    SoleSettlementCard(),
    LargestIslandCard(),
    SmallestIslandCard(),
)
