from collections import Counter, deque
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol, Self

from .core import BoatId, ClanColor, SpaceId, SpaceKind
from .structures import Stack, UnionFind


@dataclass(frozen=True, slots=True)
class TempleTile:
    type_id: int
    victory_points: int


type SpaceState = tuple[
    ClanColor | None, bool, tuple[ClanColor, ...], BoatId | None, tuple[TempleTile, ...]
]
type SwampState = tuple[dict[SpaceId, SpaceState], SpaceId, dict[BoatId, SpaceId]]


class SpaceView(Protocol):
    @property
    def id(self) -> SpaceId: ...
    @property
    def kind(self) -> SpaceKind: ...
    @property
    def fishing(self) -> bool: ...
    @property
    def settlement(self) -> ClanColor | None: ...
    @property
    def spirit_added(self) -> bool: ...
    @property
    def boat(self) -> BoatId | None: ...
    @property
    def fish_count(self) -> int: ...
    @property
    def is_land(self) -> bool: ...
    @property
    def spirit_value(self) -> int: ...
    @property
    def temple_reward(self) -> int: ...


class IslandView(Protocol):
    @property
    def spaces(self) -> frozenset[SpaceId]: ...
    @property
    def size(self) -> int: ...
    @property
    def spirit_count(self) -> int: ...
    @property
    def has_totem(self) -> bool: ...
    def settlements(self, color: ClanColor) -> int: ...
    def __contains__(self, space_id: SpaceId) -> bool: ...
    def __len__(self) -> int: ...


class BoardView(Protocol):
    @property
    def totem(self) -> SpaceId: ...
    @property
    def player_count(self) -> int: ...
    def space(self, space_id: SpaceId) -> SpaceView: ...
    def spaces(self) -> tuple[SpaceView, ...]: ...
    def neighbours(self, space_id: SpaceId) -> frozenset[SpaceId]: ...
    def islands(self) -> tuple[IslandView, ...]: ...
    def island_containing(self, space_id: SpaceId) -> IslandView: ...
    def reachable(
        self, start: SpaceId, steps: int, include_temple: bool
    ) -> frozenset[SpaceId]: ...


class Space:
    __slots__ = (
        "_id",
        "_kind",
        "_fishing",
        "_settlement",
        "_spirit_added",
        "_fish",
        "_boat",
        "_temples",
    )

    _id: SpaceId
    _kind: SpaceKind
    _fishing: bool
    _settlement: ClanColor | None
    _spirit_added: bool
    _fish: Stack[ClanColor]
    _boat: BoatId | None
    _temples: Stack[TempleTile]

    def __new__(cls) -> Self:
        raise TypeError("Spaces are created by the swamp, not directly.")

    @classmethod
    def _new(cls, space_id: SpaceId, kind: SpaceKind, fishing: bool) -> Self:
        self = object.__new__(cls)
        self._id = space_id
        self._kind = kind
        self._fishing = fishing
        self._settlement = None
        self._spirit_added = False
        self._fish = Stack()
        self._boat = None
        self._temples = Stack()
        return self

    @property
    def id(self) -> SpaceId:
        return self._id

    @property
    def kind(self) -> SpaceKind:
        return self._kind

    @property
    def fishing(self) -> bool:
        return self._fishing

    @property
    def settlement(self) -> ClanColor | None:
        return self._settlement

    @property
    def spirit_added(self) -> bool:
        return self._spirit_added

    @property
    def boat(self) -> BoatId | None:
        return self._boat

    @property
    def fish_count(self) -> int:
        return len(self._fish)

    @property
    def is_land(self) -> bool:
        return (
            self._kind is SpaceKind.SPIRIT
            or self._settlement is not None
            or self._spirit_added
        )

    @property
    def spirit_value(self) -> int:
        return 1 if (self._kind is SpaceKind.SPIRIT or self._spirit_added) else 0

    @property
    def temple_reward(self) -> int:
        return self._temples.peek().victory_points if self._temples else 0

    @property
    def temple_top(self) -> TempleTile | None:
        return self._temples.peek() if self._temples else None

    def _build(self, color: ClanColor) -> None:
        self._settlement = color

    def _add_spirit(self) -> None:
        self._spirit_added = True

    def _dock(self, boat: BoatId) -> None:
        self._boat = boat

    def _undock(self) -> None:
        self._boat = None

    def _push_fish(self, color: ClanColor) -> None:
        self._fish.push(color)

    def _drain_fish(self) -> None:
        self._fish.replace(())

    def _add_temple(self, tile: TempleTile) -> None:
        self._temples.push(tile)

    def _pop_temple(self) -> TempleTile | None:
        return self._temples.pop() if self._temples else None

    def _capture(self) -> SpaceState:
        return (
            self._settlement,
            self._spirit_added,
            self._fish.snapshot(),
            self._boat,
            self._temples.snapshot(),
        )

    def _restore(self, state: SpaceState) -> None:
        self._settlement = state[0]
        self._spirit_added = state[1]
        self._fish.replace(state[2])
        self._boat = state[3]
        self._temples.replace(state[4])


class Island:
    __slots__ = ("_ids", "_spirit_count", "_has_totem", "_settlement_counts")

    _ids: frozenset[SpaceId]
    _spirit_count: int
    _has_totem: bool
    _settlement_counts: Counter[ClanColor]

    def __new__(cls) -> Self:
        raise TypeError("Islands are created by the swamp, not directly.")

    @classmethod
    def _new(cls, members: tuple[Space, ...], has_totem: bool) -> Self:
        self = object.__new__(cls)
        self._ids = frozenset(member.id for member in members)
        self._spirit_count = sum(member.spirit_value for member in members)
        self._has_totem = has_totem
        self._settlement_counts = Counter(
            member.settlement for member in members if member.settlement is not None
        )
        return self

    @property
    def spaces(self) -> frozenset[SpaceId]:
        return self._ids

    @property
    def size(self) -> int:
        return len(self._ids)

    @property
    def spirit_count(self) -> int:
        return self._spirit_count

    @property
    def has_totem(self) -> bool:
        return self._has_totem

    def settlements(self, color: ClanColor) -> int:
        return self._settlement_counts[color]

    def __contains__(self, space_id: SpaceId) -> bool:
        return space_id in self._ids

    def __iter__(self) -> Iterator[SpaceId]:
        return iter(self._ids)

    def __len__(self) -> int:
        return len(self._ids)


class Swamp:
    __slots__ = ("_spaces", "_adjacency", "_totem", "_player_count", "_boat_space")

    _spaces: dict[SpaceId, Space]
    _adjacency: dict[SpaceId, frozenset[SpaceId]]
    _totem: SpaceId
    _player_count: int
    _boat_space: dict[BoatId, SpaceId]

    def __new__(cls) -> Self:
        raise TypeError("The swamp is created by the game, not directly.")

    @classmethod
    def _new(
        cls,
        spaces: dict[SpaceId, Space],
        adjacency: dict[SpaceId, frozenset[SpaceId]],
        totem: SpaceId,
        player_count: int,
    ) -> Self:
        self = object.__new__(cls)
        self._spaces = spaces
        self._adjacency = adjacency
        self._totem = totem
        self._player_count = player_count
        self._boat_space = {}
        return self

    @property
    def totem(self) -> SpaceId:
        return self._totem

    @property
    def player_count(self) -> int:
        return self._player_count

    def space(self, space_id: SpaceId) -> Space:
        if space_id not in self._spaces:
            raise KeyError(space_id)
        return self._spaces[space_id]

    def spaces(self) -> tuple[Space, ...]:
        return tuple(self._spaces.values())

    def neighbours(self, space_id: SpaceId) -> frozenset[SpaceId]:
        return self._adjacency[space_id]

    def boat_space(self, boat: BoatId) -> SpaceId:
        return self._boat_space[boat]

    def reachable(
        self, start: SpaceId, steps: int, include_temple: bool
    ) -> frozenset[SpaceId]:
        distance: dict[SpaceId, int] = {start: 0}
        queue: deque[SpaceId] = deque([start])
        endpoints: set[SpaceId] = set()
        while queue:
            current = queue.popleft()
            depth = distance[current]
            if depth >= steps:
                continue
            for neighbour in self._adjacency[current]:
                if neighbour in distance:
                    continue
                space = self._spaces[neighbour]
                match space.kind:
                    case SpaceKind.TEMPLE:
                        if include_temple:
                            distance[neighbour] = depth + 1
                            endpoints.add(neighbour)
                    case SpaceKind.SPIRIT:
                        continue
                    case SpaceKind.WATER:
                        if space.is_land:
                            continue
                        distance[neighbour] = depth + 1
                        queue.append(neighbour)
                        if space.boat is None:
                            endpoints.add(neighbour)
        return frozenset(endpoints)

    def _land_union(self) -> UnionFind[SpaceId]:
        union: UnionFind[SpaceId] = UnionFind()
        land = [sid for sid, space in self._spaces.items() if space.is_land]
        for sid in land:
            union.add(sid)
        for sid in land:
            for neighbour in self._adjacency[sid]:
                if self._spaces[neighbour].is_land:
                    union.union(sid, neighbour)
        return union

    def islands(self) -> tuple[Island, ...]:
        result: list[Island] = []
        for component in self._land_union().components():
            members = tuple(self._spaces[sid] for sid in component)
            result.append(Island._new(members, self._totem in component))
        return tuple(result)

    def island_containing(self, space_id: SpaceId) -> Island:
        for island in self.islands():
            if space_id in island:
                return island
        return Island._new((self._spaces[space_id],), self._totem == space_id)

    def adjacent_islands(self, space_id: SpaceId) -> tuple[Island, ...]:
        islands = self.islands()
        found: list[Island] = []
        seen: set[frozenset[SpaceId]] = set()
        for neighbour in self._adjacency[space_id]:
            if not self._spaces[neighbour].is_land:
                continue
            for island in islands:
                if neighbour in island and island.spaces not in seen:
                    found.append(island)
                    seen.add(island.spaces)
                    break
        return tuple(found)

    def would_join_islands(self, space_id: SpaceId) -> bool:
        return len(self.adjacent_islands(space_id)) >= 2

    def is_adjacent_to_land(self, space_id: SpaceId) -> bool:
        return any(self._spaces[n].is_land for n in self._adjacency[space_id])

    def is_adjacent_to_settlement(self, space_id: SpaceId) -> bool:
        return any(
            self._spaces[n].settlement is not None for n in self._adjacency[space_id]
        )

    def adjacent_settlements(self, space_id: SpaceId) -> tuple[SpaceId, ...]:
        return tuple(
            n
            for n in self._adjacency[space_id]
            if self._spaces[n].settlement is not None
        )

    def settlements_of(self, color: ClanColor) -> tuple[SpaceId, ...]:
        return tuple(
            sid for sid, space in self._spaces.items() if space.settlement is color
        )

    def _place_boat(self, boat: BoatId, space_id: SpaceId) -> None:
        self._spaces[space_id]._dock(boat)
        self._boat_space[boat] = space_id

    def _move_boat(self, boat: BoatId, destination: SpaceId) -> None:
        origin = self._boat_space[boat]
        self._spaces[origin]._undock()
        self._spaces[destination]._dock(boat)
        self._boat_space[boat] = destination

    def _build_settlement(self, space_id: SpaceId, color: ClanColor) -> None:
        self._spaces[space_id]._build(color)

    def _add_spirit(self, space_id: SpaceId) -> None:
        self._spaces[space_id]._add_spirit()
        self._totem = space_id

    def _capture(self) -> SwampState:
        snapshot = {sid: space._capture() for sid, space in self._spaces.items()}
        return snapshot, self._totem, dict(self._boat_space)

    def _restore(self, state: SwampState) -> None:
        for sid, space_state in state[0].items():
            self._spaces[sid]._restore(space_state)
        self._totem = state[1]
        self._boat_space = dict(state[2])


_GRID_WIDTH = 7
_GRID_HEIGHT = 6
_SPIRIT_CELLS = ((1, 1), (1, 5), (4, 1), (4, 5), (2, 3), (5, 3))
_TEMPLE_CELLS = ((0, 0), (0, 6), (5, 0), (5, 6))
_FISHING_CELLS = ((0, 3), (2, 0), (2, 6), (3, 3), (4, 3), (1, 3), (3, 0), (3, 6))
_TOTEM_CELL = (2, 3)
_TEMPLE_REWARDS = (5, 4, 3, 2)


def _cell_id(row: int, column: int) -> SpaceId:
    return row * _GRID_WIDTH + column


def build_swamp(player_count: int) -> Swamp:
    spirits = {_cell_id(r, c) for r, c in _SPIRIT_CELLS}
    temples = {_cell_id(r, c) for r, c in _TEMPLE_CELLS}
    fishing = {_cell_id(r, c) for r, c in _FISHING_CELLS}
    spaces: dict[SpaceId, Space] = {}
    for row in range(_GRID_HEIGHT):
        for column in range(_GRID_WIDTH):
            sid = _cell_id(row, column)
            if sid in spirits:
                kind = SpaceKind.SPIRIT
            elif sid in temples:
                kind = SpaceKind.TEMPLE
            else:
                kind = SpaceKind.WATER
            spaces[sid] = Space._new(
                sid, kind, sid in fishing and kind is SpaceKind.WATER
            )
    adjacency: dict[SpaceId, frozenset[SpaceId]] = {}
    for row in range(_GRID_HEIGHT):
        for column in range(_GRID_WIDTH):
            sid = _cell_id(row, column)
            linked: set[SpaceId] = set()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = row + dr, column + dc
                if 0 <= nr < _GRID_HEIGHT and 0 <= nc < _GRID_WIDTH:
                    linked.add(_cell_id(nr, nc))
            adjacency[sid] = frozenset(linked)
    for index, sid in enumerate(sorted(temples)):
        for reward in reversed(_TEMPLE_REWARDS):
            spaces[sid]._add_temple(TempleTile(index, reward))
    return Swamp._new(spaces, adjacency, _cell_id(*_TOTEM_CELL), player_count)


def starting_spaces(swamp: Swamp) -> tuple[SpaceId, ...]:
    result: list[SpaceId] = []
    for space in swamp.spaces():
        if space.kind is SpaceKind.WATER and not space.is_land and space.boat is None:
            if swamp.is_adjacent_to_land(space.id):
                result.append(space.id)
    return tuple(result)
