from typing import Self

from .board import Island, IslandView, Space, SpaceView, Swamp
from .core import BoatId, ClanColor, SpaceId, SpaceKind
from .guides import GuideView
from .players import Player, PlayerView


class SpaceProxy:
    __slots__ = ("_space",)

    _space: Space

    def __new__(cls, space: Space) -> Self:
        self = super().__new__(cls)
        self._space = space
        return self

    @property
    def id(self) -> SpaceId:
        return self._space.id

    @property
    def kind(self) -> SpaceKind:
        return self._space.kind

    @property
    def fishing(self) -> bool:
        return self._space.fishing

    @property
    def settlement(self) -> ClanColor | None:
        return self._space.settlement

    @property
    def spirit_added(self) -> bool:
        return self._space.spirit_added

    @property
    def boat(self) -> BoatId | None:
        return self._space.boat

    @property
    def fish_count(self) -> int:
        return self._space.fish_count

    @property
    def is_land(self) -> bool:
        return self._space.is_land

    @property
    def spirit_value(self) -> int:
        return self._space.spirit_value

    @property
    def temple_reward(self) -> int:
        return self._space.temple_reward


class IslandProxy:
    __slots__ = ("_island",)

    _island: Island

    def __new__(cls, island: Island) -> Self:
        self = super().__new__(cls)
        self._island = island
        return self

    @property
    def spaces(self) -> frozenset[SpaceId]:
        return self._island.spaces

    @property
    def size(self) -> int:
        return self._island.size

    @property
    def spirit_count(self) -> int:
        return self._island.spirit_count

    @property
    def has_totem(self) -> bool:
        return self._island.has_totem

    def settlements(self, color: ClanColor) -> int:
        return self._island.settlements(color)

    def __contains__(self, space_id: SpaceId) -> bool:
        return space_id in self._island

    def __len__(self) -> int:
        return len(self._island)


class BoardProxy:
    __slots__ = ("_swamp",)

    _swamp: Swamp

    def __new__(cls, swamp: Swamp) -> Self:
        self = super().__new__(cls)
        self._swamp = swamp
        return self

    @property
    def totem(self) -> SpaceId:
        return self._swamp.totem

    @property
    def player_count(self) -> int:
        return self._swamp.player_count

    def space(self, space_id: SpaceId) -> SpaceView:
        return SpaceProxy(self._swamp.space(space_id))

    def spaces(self) -> tuple[SpaceView, ...]:
        return tuple(SpaceProxy(space) for space in self._swamp.spaces())

    def neighbours(self, space_id: SpaceId) -> frozenset[SpaceId]:
        return self._swamp.neighbours(space_id)

    def islands(self) -> tuple[IslandView, ...]:
        return tuple(IslandProxy(island) for island in self._swamp.islands())

    def island_containing(self, space_id: SpaceId) -> IslandView:
        return IslandProxy(self._swamp.island_containing(space_id))

    def reachable(
        self, start: SpaceId, steps: int, include_temple: bool
    ) -> frozenset[SpaceId]:
        return self._swamp.reachable(start, steps, include_temple)


class PlayerProxy:
    __slots__ = ("_player",)

    _player: Player

    def __new__(cls, player: Player) -> Self:
        self = super().__new__(cls)
        self._player = player
        return self

    @property
    def color(self) -> ClanColor:
        return self._player.color

    @property
    def score(self) -> int:
        return self._player.score

    @property
    def gold(self) -> int:
        return self._player.gold

    @property
    def mana(self) -> int:
        return self._player.mana

    @property
    def fish(self) -> int:
        return self._player.fish

    @property
    def workers_available(self) -> int:
        return self._player.workers_available

    @property
    def neutral_available(self) -> int:
        return self._player.neutral_available

    @property
    def sailing_value(self) -> int:
        return self._player.sailing_value

    @property
    def guide(self) -> GuideView | None:
        return self._player.guide

    @property
    def passed(self) -> bool:
        return self._player.passed

    @property
    def temple_count(self) -> int:
        return self._player.temple_count

    @property
    def boats(self) -> tuple[BoatId, ...]:
        return self._player.boats
