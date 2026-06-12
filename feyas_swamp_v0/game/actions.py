from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Final, Protocol, Self

from .board import Swamp
from .core import (
    ActionKind,
    BoatId,
    CELEBRATE_TOTEM_BONUS,
    ClanColor,
    IllegalMove,
    IllegalPlacement,
    InsufficientResources,
    MAX_FISH_STACK,
    Resource,
    SpaceId,
    SpaceKind,
    SPIRIT_BUILD_COST,
    TOTEM_TRADE_BONUS,
    TRADE_REWARD,
)
from .players import Player


class ActionContext(Protocol):
    @property
    def swamp(self) -> Swamp: ...
    @property
    def colors(self) -> tuple[ClanColor, ...]: ...
    def player(self, color: ClanColor) -> Player: ...
    def award(self, color: ClanColor, points: int) -> None: ...
    def sailing_range(self, color: ClanColor, sailing_action: bool) -> int: ...
    def fishing_capacity(self, color: ClanColor) -> int: ...
    def build_discount(self, color: ClanColor) -> int: ...
    def settlement_value(self, color: ClanColor) -> int: ...


class PlacementRule(ABC):
    __slots__ = ("_successor",)

    _successor: PlacementRule | None

    def __new__(cls, successor: PlacementRule | None = None) -> Self:
        self = super().__new__(cls)
        self._successor = successor
        return self

    @abstractmethod
    def _check(self, swamp: Swamp, space_id: SpaceId) -> None: ...

    def handle(self, swamp: Swamp, space_id: SpaceId) -> None:
        self._check(swamp, space_id)
        if self._successor is not None:
            self._successor.handle(swamp, space_id)


class FreeWaterRule(PlacementRule):
    __slots__ = ()

    def _check(self, swamp: Swamp, space_id: SpaceId) -> None:
        space = swamp.space(space_id)
        if space.kind is not SpaceKind.WATER or space.is_land or space.boat is not None:
            raise IllegalPlacement("space is not free water")


class AdjacentToLandRule(PlacementRule):
    __slots__ = ()

    def _check(self, swamp: Swamp, space_id: SpaceId) -> None:
        if not swamp.is_adjacent_to_land(space_id):
            raise IllegalPlacement("not adjacent to an island")


class NoJoinIslandsRule(PlacementRule):
    __slots__ = ()

    def _check(self, swamp: Swamp, space_id: SpaceId) -> None:
        if swamp.would_join_islands(space_id):
            raise IllegalPlacement("would join two islands")


class NotTotemIslandRule(PlacementRule):
    __slots__ = ()

    def _check(self, swamp: Swamp, space_id: SpaceId) -> None:
        for island in swamp.adjacent_islands(space_id):
            if island.has_totem:
                raise IllegalPlacement("island already holds the totem")


BUILD_RULES: Final[PlacementRule] = FreeWaterRule(
    AdjacentToLandRule(NoJoinIslandsRule())
)
SPIRIT_RULES: Final[PlacementRule] = FreeWaterRule(
    AdjacentToLandRule(NotTotemIslandRule(NoJoinIslandsRule()))
)


class Action(ABC):
    __slots__ = ("_context", "_color")

    _context: ActionContext
    _color: ClanColor

    def __new__(cls, context: ActionContext, color: ClanColor) -> Self:
        self = super().__new__(cls)
        self._context = context
        self._color = color
        return self

    @property
    @abstractmethod
    def kind(self) -> ActionKind: ...

    @property
    def color(self) -> ClanColor:
        return self._color

    @abstractmethod
    def _validate(self) -> None: ...

    @abstractmethod
    def _apply(self) -> None: ...

    def run(self) -> None:
        self._validate()
        self._apply()

    def _actor(self) -> Player:
        return self._context.player(self._color)

    def _require_worker(self) -> None:
        if self._actor().workers_available <= 0:
            raise InsufficientResources("no workers available")


class BoatAction(Action):
    __slots__ = ("_moves",)

    _moves: dict[BoatId, SpaceId]

    def __new__(
        cls, context: ActionContext, color: ClanColor, moves: Mapping[BoatId, SpaceId]
    ) -> Self:
        self = super().__new__(cls, context, color)
        self._moves = dict(moves)
        return self

    def _allow_temple(self) -> bool:
        return False

    @abstractmethod
    def _check_target(self, destination: SpaceId) -> None: ...

    @abstractmethod
    def _effect(self, boat: BoatId, destination: SpaceId) -> None: ...

    def _extra_validation(self) -> None:
        return None

    def _validate(self) -> None:
        self._require_worker()
        if not self._moves:
            raise IllegalMove("no boats moved")
        destinations = list(self._moves.values())
        if len(set(destinations)) != len(destinations):
            raise IllegalMove("two boats target the same space")
        actor = self._actor()
        swamp = self._context.swamp
        owned = set(actor.boats)
        steps = self._context.sailing_range(self._color, self.kind is ActionKind.SAIL)
        for boat, destination in self._moves.items():
            if boat not in owned:
                raise IllegalMove("boat is not owned by this clan")
            origin = swamp.boat_space(boat)
            if destination not in swamp.reachable(origin, steps, self._allow_temple()):
                raise IllegalMove("destination is out of range")
            self._check_target(destination)
        self._extra_validation()

    def _apply(self) -> None:
        self._actor()._use_worker()
        for boat, destination in self._moves.items():
            self._effect(boat, destination)


class FishAction(BoatAction):
    __slots__ = ()

    @property
    def kind(self) -> ActionKind:
        return ActionKind.FISH

    def _check_target(self, destination: SpaceId) -> None:
        if not self._context.swamp.space(destination).fishing:
            raise IllegalMove("no fish at destination")

    def _effect(self, boat: BoatId, destination: SpaceId) -> None:
        swamp = self._context.swamp
        swamp._move_boat(boat, destination)
        self._actor()._gain(Resource.FISH, self._context.fishing_capacity(self._color))


class BuildAction(BoatAction):
    __slots__ = ()

    @property
    def kind(self) -> ActionKind:
        return ActionKind.BUILD

    def _check_target(self, destination: SpaceId) -> None:
        BUILD_RULES.handle(self._context.swamp, destination)

    def _target_cost(self, destination: SpaceId) -> int:
        swamp = self._context.swamp
        islands = swamp.adjacent_islands(destination)
        spirits = islands[0].spirit_count if islands else 0
        value = self._context.settlement_value(self._color)
        discount = self._context.build_discount(self._color)
        return max(0, SPIRIT_BUILD_COST * spirits + value - discount)

    def _extra_validation(self) -> None:
        total = sum(self._target_cost(dest) for dest in self._moves.values())
        if self._actor().gold < total:
            raise InsufficientResources("not enough gold to build")

    def _effect(self, boat: BoatId, destination: SpaceId) -> None:
        swamp = self._context.swamp
        BUILD_RULES.handle(swamp, destination)
        cost = self._target_cost(destination)
        self._actor()._spend(Resource.GOLD, cost)
        swamp._build_settlement(destination, self._color)
        swamp._move_boat(boat, destination)


class SailAction(BoatAction):
    __slots__ = ()

    @property
    def kind(self) -> ActionKind:
        return ActionKind.SAIL

    def _allow_temple(self) -> bool:
        return True

    def _check_target(self, destination: SpaceId) -> None:
        return None

    def _effect(self, boat: BoatId, destination: SpaceId) -> None:
        swamp = self._context.swamp
        space = swamp.space(destination)
        top = space.temple_top
        if (
            space.kind is SpaceKind.TEMPLE
            and top is not None
            and not self._actor().has_temple_type(top.type_id)
        ):
            space._pop_temple()
            self._actor()._add_temple(top)
            self._context.award(self._color, top.victory_points)
        swamp._move_boat(boat, destination)


class TradeAction(BoatAction):
    __slots__ = ("_placements",)

    _placements: dict[BoatId, tuple[SpaceId, ...]]

    def __new__(
        cls,
        context: ActionContext,
        color: ClanColor,
        moves: Mapping[BoatId, SpaceId],
        placements: Mapping[BoatId, Sequence[SpaceId]],
    ) -> Self:
        self = super().__new__(cls, context, color, moves)
        self._placements = {boat: tuple(spots) for boat, spots in placements.items()}
        return self

    @property
    def kind(self) -> ActionKind:
        return ActionKind.TRADE

    def _check_target(self, destination: SpaceId) -> None:
        if not self._context.swamp.is_adjacent_to_settlement(destination):
            raise IllegalMove("no settlement adjacent to destination")

    def _extra_validation(self) -> None:
        swamp = self._context.swamp
        planned: dict[SpaceId, int] = {}
        total_fish = 0
        for boat, spots in self._placements.items():
            if boat not in self._moves:
                raise IllegalMove("placement for a boat that did not move")
            adjacent = set(swamp.adjacent_settlements(self._moves[boat]))
            for target in spots:
                if target not in adjacent:
                    raise IllegalMove("settlement not adjacent to boat")
                planned[target] = planned.get(target, 0) + 1
                total_fish += 1
        for target, count in planned.items():
            if swamp.space(target).fish_count + count > MAX_FISH_STACK:
                raise IllegalMove("fish stack would overflow")
        if self._actor().fish < total_fish:
            raise InsufficientResources("not enough fish to trade")

    def _effect(self, boat: BoatId, destination: SpaceId) -> None:
        swamp = self._context.swamp
        swamp._move_boat(boat, destination)
        actor = self._actor()
        for target in self._placements.get(boat, ()):
            space = swamp.space(target)
            position = space.fish_count
            owner = space.settlement
            actor._spend(Resource.FISH, 1)
            space._push_fish(self._color)
            if owner is not None and owner is not self._color:
                reward = TRADE_REWARD[position]
                if swamp.island_containing(target).has_totem:
                    reward += TOTEM_TRADE_BONUS
                actor._gain(Resource.GOLD, reward)


class ImproveSailingAction(Action):
    __slots__ = ()

    @property
    def kind(self) -> ActionKind:
        return ActionKind.IMPROVE_SAILING

    def _validate(self) -> None:
        self._require_worker()

    def _apply(self) -> None:
        actor = self._actor()
        actor._use_worker()
        self._context.award(self._color, actor._advance_sailing())


def celebrate_island(
    context: ActionContext, color: ClanColor, ids: frozenset[SpaceId]
) -> None:
    swamp = context.swamp
    with_fish = sum(
        1
        for sid in ids
        if swamp.space(sid).settlement is not None and swamp.space(sid).fish_count > 0
    )
    context.award(color, with_fish)
    if swamp.totem in ids:
        context.award(color, CELEBRATE_TOTEM_BONUS)
    for other in context.colors:
        total = sum(
            swamp.space(sid).fish_count
            for sid in ids
            if swamp.space(sid).settlement is other
        )
        if total:
            context.award(other, total)
    for sid in ids:
        swamp.space(sid)._drain_fish()


class CelebrateAction(Action):
    __slots__ = ("_anchor",)

    _anchor: SpaceId

    def __new__(cls, context: ActionContext, color: ClanColor, anchor: SpaceId) -> Self:
        self = super().__new__(cls, context, color)
        self._anchor = anchor
        return self

    @property
    def kind(self) -> ActionKind:
        return ActionKind.CELEBRATE

    def _validate(self) -> None:
        self._require_worker()
        if not self._context.swamp.space(self._anchor).is_land:
            raise IllegalMove("celebration anchor is not on an island")

    def _apply(self) -> None:
        self._actor()._use_worker()
        island = self._context.swamp.island_containing(self._anchor)
        celebrate_island(self._context, self._color, island.spaces)


class AddSpiritAction(Action):
    __slots__ = ("_target",)

    _target: SpaceId

    def __new__(cls, context: ActionContext, color: ClanColor, target: SpaceId) -> Self:
        self = super().__new__(cls, context, color)
        self._target = target
        return self

    @property
    def kind(self) -> ActionKind:
        return ActionKind.ADD_SPIRIT

    def _validate(self) -> None:
        self._require_worker()
        SPIRIT_RULES.handle(self._context.swamp, self._target)

    def _apply(self) -> None:
        self._actor()._use_worker()
        self._context.swamp._add_spirit(self._target)
