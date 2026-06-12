from collections.abc import Callable
from types import MappingProxyType
from typing import Self

from .actions import Action, celebrate_island
from .board import Swamp, SwampState
from .core import (
    ActionKind,
    ClanColor,
    GOLD_VP_DIVISOR,
    GuideKind,
    IllegalMove,
    IllegalSetup,
    INCOME_GOLD_PER_SETTLEMENT,
    INCOME_MANA,
    InsufficientResources,
    MANA_PER_NEUTRAL,
    NotYourTurn,
    Observable,
    Phase,
    Resource,
    SAIL_MAP_BONUS,
    SAIL_MAP_BONUS_MIN_PLAYERS,
    ScoreEvent,
    SpaceId,
    SpaceKind,
    STARTING_SETTLEMENTS,
    WORKER_TO_MANA,
    WrongPhase,
)
from .guides import GUIDES, GuideCard, ability_for
from .phases import DraftPhase, PhaseState
from .players import Bank, Player, PlayerState, PlayerView
from .scoring import ScoreCard, ScoreCardView, islands_led
from .views import BoardProxy, PlayerProxy

type GameSnapshot = tuple[SwampState, dict[ClanColor, PlayerState], int, int]


class Engine:
    __slots__ = (
        "_swamp",
        "_bank",
        "_players",
        "_order",
        "_offer",
        "_score_cards",
        "_state",
        "_round",
        "_cursor",
        "_draft_order",
        "_draft_index",
        "_placement_seq",
        "_placement_index",
        "_last_memento",
        "_scores",
    )

    _swamp: Swamp
    _bank: Bank
    _players: dict[ClanColor, Player]
    _order: list[ClanColor]
    _offer: list[GuideKind]
    _score_cards: tuple[ScoreCard, ...]
    _state: PhaseState
    _round: int
    _cursor: int
    _draft_order: list[ClanColor]
    _draft_index: int
    _placement_seq: list[ClanColor]
    _placement_index: int
    _last_memento: GameSnapshot | None
    _scores: Observable[ScoreEvent]

    def __new__(cls) -> Self:
        raise TypeError("The engine is created by the game, not directly.")

    @classmethod
    def _new(
        cls,
        swamp: Swamp,
        bank: Bank,
        players: dict[ClanColor, Player],
        order: list[ClanColor],
        offer: list[GuideKind],
        score_cards: tuple[ScoreCard, ...],
    ) -> Self:
        self = object.__new__(cls)
        self._swamp = swamp
        self._bank = bank
        self._players = players
        self._order = []
        self._offer = offer
        self._score_cards = score_cards
        self._state = DraftPhase()
        self._round = 0
        self._cursor = 0
        self._draft_order = order
        self._draft_index = 0
        self._placement_seq = []
        self._placement_index = 0
        self._last_memento = None
        self._scores = Observable()
        return self

    @property
    def swamp(self) -> Swamp:
        return self._swamp

    def board_view(self) -> BoardProxy:
        return BoardProxy(self._swamp)

    @property
    def colors(self) -> tuple[ClanColor, ...]:
        return tuple(self._draft_order)

    @property
    def phase(self) -> Phase:
        return self._state.phase

    @property
    def round_number(self) -> int:
        return self._round

    @property
    def is_over(self) -> bool:
        return self._state.phase is Phase.OVER

    @property
    def turn_order(self) -> tuple[ClanColor, ...]:
        return tuple(self._order)

    @property
    def offer(self) -> tuple[GuideCard, ...]:
        return tuple(GUIDES[kind] for kind in self._offer)

    def score_cards(self) -> tuple[ScoreCardView, ...]:
        return self._score_cards

    def player(self, color: ClanColor) -> Player:
        if color not in self._players:
            raise IllegalMove("unknown clan")
        return self._players[color]

    def players_view(self) -> MappingProxyType[ClanColor, PlayerView]:
        views: dict[ClanColor, PlayerView] = {
            color: PlayerProxy(player) for color, player in self._players.items()
        }
        return MappingProxyType(views)

    def scores(self) -> MappingProxyType[ClanColor, int]:
        return MappingProxyType({c: p.score for c, p in self._players.items()})

    def subscribe(self, callback: Callable[[ScoreEvent], None]) -> None:
        self._scores.subscribe(callback)

    def winners(self) -> frozenset[ClanColor]:
        if self._state.phase is not Phase.OVER:
            return frozenset()
        best = max(player.score for player in self._players.values())
        return frozenset(c for c, p in self._players.items() if p.score == best)

    def legal_actions(self) -> frozenset[ActionKind]:
        if not self._state.allows_turn:
            return frozenset()
        current = self._current()
        if current is None:
            return frozenset()
        kinds = {ActionKind.PASS}
        if self._players[current].workers_available > 0:
            kinds |= {
                ActionKind.FISH,
                ActionKind.BUILD,
                ActionKind.SAIL,
                ActionKind.TRADE,
                ActionKind.IMPROVE_SAILING,
                ActionKind.CELEBRATE,
                ActionKind.ADD_SPIRIT,
            }
        return frozenset(kinds)

    def current_actor(self) -> ClanColor | None:
        if self._state.allows_draft:
            return self._draft_order[self._draft_index]
        if self._state.allows_placement:
            return self._placement_seq[self._placement_index]
        if self._state.allows_turn:
            return self._current()
        return None

    def award(self, color: ClanColor, points: int) -> None:
        self._players[color]._award(points)
        self._scores._notify((color, self._players[color].score))

    def gain(self, color: ClanColor, resource: Resource, amount: int) -> None:
        self._players[color]._gain(resource, amount)

    def add_neutral(self, color: ClanColor, count: int) -> None:
        taken = self._bank._take_neutral(count)
        self._players[color]._add_neutral(taken)

    def advance_sailing(self, color: ClanColor) -> None:
        self.award(color, self._players[color]._advance_sailing())

    def temple_count(self, color: ClanColor) -> int:
        return self._players[color].temple_count

    def islands_led(self, color: ClanColor) -> int:
        return islands_led(self._swamp, color, self.colors)

    def celebrate_best(self, color: ClanColor) -> None:
        swamp = self._swamp
        chosen: frozenset[SpaceId] | None = None
        best = -1
        for island in swamp.islands():
            value = sum(
                1
                for sid in island
                if swamp.space(sid).settlement is not None
                and swamp.space(sid).fish_count > 0
            )
            if value > best:
                best, chosen = value, island.spaces
        if chosen is None:
            return
        celebrate_island(self, color, chosen)

    def sailing_range(self, color: ClanColor, sailing_action: bool) -> int:
        player = self._players[color]
        guide = player.guide
        base = guide.sailing_range if guide is not None else 0
        bonus = (
            SAIL_MAP_BONUS
            if sailing_action and self._swamp.player_count >= SAIL_MAP_BONUS_MIN_PLAYERS
            else 0
        )
        return base + player.sailing_value + bonus

    def fishing_capacity(self, color: ClanColor) -> int:
        guide = self._players[color].guide
        bonus = ability_for(guide).fishing_bonus if guide is not None else 0
        return 1 + bonus

    def build_discount(self, color: ClanColor) -> int:
        guide = self._players[color].guide
        return ability_for(guide).build_discount if guide is not None else 0

    def settlement_value(self, color: ClanColor) -> int:
        guide = self._players[color].guide
        return guide.settlement_value if guide is not None else 0

    def draft_guide(self, color: ClanColor, guide: GuideKind) -> None:
        if not self._state.allows_draft:
            raise WrongPhase("not the drafting phase")
        if color != self._draft_order[self._draft_index]:
            raise IllegalSetup("not this clan's turn to draft")
        if guide not in self._offer:
            raise IllegalSetup("guide not available")
        self.player(color)._set_guide(GUIDES[guide])
        self._offer.remove(guide)
        self._draft_index += 1
        if self._draft_index == len(self._draft_order):
            self._state = self._state.advance(self)

    def _finish_drafting(self) -> None:
        self._order = sorted(self._draft_order, key=self._initiative)
        self._placement_seq = list(self._order) * STARTING_SETTLEMENTS
        self._placement_index = 0

    def _initiative(self, color: ClanColor) -> int:
        guide = self._players[color].guide
        return guide.initiative if guide is not None else 99

    def place_starting_settlement(self, color: ClanColor, space: SpaceId) -> None:
        if not self._state.allows_placement:
            raise WrongPhase("not the placement phase")
        if color != self._placement_seq[self._placement_index]:
            raise IllegalSetup("not this clan's turn to place")
        self._validate_start(color, space)
        index = len(self._swamp.settlements_of(color))
        boat = self.player(color).boats[index]
        self._swamp._build_settlement(space, color)
        self._swamp._place_boat(boat, space)
        self._placement_index += 1
        if self._placement_index == len(self._placement_seq):
            self._state = self._state.advance(self)

    def _validate_start(self, color: ClanColor, space: SpaceId) -> None:
        swamp = self._swamp
        cell = swamp.space(space)
        if cell.kind is not SpaceKind.WATER or cell.is_land or cell.boat is not None:
            raise IllegalSetup("space is not free water")
        if not any(swamp.space(n).spirit_value > 0 for n in swamp.neighbours(space)):
            raise IllegalSetup("not adjacent to a spirit space")
        for island in swamp.adjacent_islands(space):
            if any(swamp.space(sid).settlement is color for sid in island):
                raise IllegalSetup("clan already present on this island")
        if swamp.would_join_islands(space):
            raise IllegalSetup("would join two islands")

    def _begin_play(self) -> None:
        self._round = 1
        self._run_income()
        self._cursor = 0

    def _run_income(self) -> None:
        for color in self._order:
            player = self._players[color]
            player._gain(Resource.MANA, INCOME_MANA)
            if self._round > 1:
                count = len(self._swamp.settlements_of(color))
                player._gain(Resource.GOLD, INCOME_GOLD_PER_SETTLEMENT * count)
            guide = player.guide
            if guide is not None:
                ability_for(guide).on_income(self, color)

    def _current(self) -> ClanColor | None:
        if not self._order:
            return None
        size = len(self._order)
        for offset in range(size):
            color = self._order[(self._cursor + offset) % size]
            if not self._players[color].passed:
                return color
        return None

    def perform(self, action: Action) -> None:
        if not self._state.allows_turn:
            raise WrongPhase("not the turns phase")
        current = self._current()
        if current is None:
            raise WrongPhase("the round is over")
        if action.color != current:
            raise NotYourTurn("not this clan's turn")
        snapshot = self._capture()
        try:
            action.run()
        except Exception:
            self._restore(snapshot)
            self._notify_scores()
            raise
        self._last_memento = snapshot
        self._cursor = (self._order.index(current) + 1) % len(self._order)

    def pass_turn(self, color: ClanColor, next_guide: GuideKind | None) -> None:
        if not self._state.allows_turn:
            raise WrongPhase("not the turns phase")
        current = self._current()
        if current is None:
            raise WrongPhase("the round is over")
        if color != current:
            raise NotYourTurn("not this clan's turn")
        player = self._players[color]
        player._pass()
        guide = player.guide
        if guide is not None:
            ability_for(guide).on_pass(self, color)
        self._draw_next_guide(player, next_guide)
        self._last_memento = None
        self._cursor = (self._order.index(color) + 1) % len(self._order)
        if self._current() is None:
            self._state = self._state.advance(self)

    def _draw_next_guide(self, player: Player, choice: GuideKind | None) -> None:
        guide = player.guide
        old = guide.kind if guide is not None else None
        picked: GuideKind | None
        if choice is not None:
            if choice not in self._offer or choice == old:
                raise IllegalMove("invalid next guide")
            self._offer.remove(choice)
            picked = choice
        else:
            candidates = [kind for kind in self._offer if kind != old]
            if candidates:
                picked = candidates[0]
                self._offer.remove(picked)
            else:
                picked = old
        if old is not None and picked != old:
            self._offer.append(old)
        if picked is not None:
            player._set_next_guide(GUIDES[picked])

    def exchange_mana_for_neutral(self, color: ClanColor) -> None:
        self._require_turn(color)
        player = self._players[color]
        if self._bank.neutral_available <= 0:
            raise IllegalMove("no neutral workers available")
        if player.mana < MANA_PER_NEUTRAL:
            raise InsufficientResources("not enough mana")
        player._spend(Resource.MANA, MANA_PER_NEUTRAL)
        self.add_neutral(color, 1)
        self._last_memento = None

    def exchange_worker_for_mana(self, color: ClanColor) -> None:
        self._require_turn(color)
        player = self._players[color]
        if player.workers_available <= 0:
            raise InsufficientResources("no workers available")
        player._use_worker()
        player._gain(Resource.MANA, WORKER_TO_MANA)
        self._last_memento = None

    def _require_turn(self, color: ClanColor) -> None:
        if not self._state.allows_turn:
            raise WrongPhase("not the turns phase")
        if self._current() != color:
            raise NotYourTurn("not this clan's turn")

    def undo(self) -> None:
        if self._last_memento is None:
            raise IllegalMove("nothing to undo")
        self._restore(self._last_memento)
        self._last_memento = None
        self._notify_scores()

    def _advance_round(self) -> None:
        self._run_maintenance()
        self._round += 1
        self._run_income()
        self._cursor = 0

    def _run_maintenance(self) -> None:
        for color in self._order:
            player = self._players[color]
            returned = player._reset_for_round()
            self._bank._return_neutral(returned)
            player._promote_guide()
        self._order = sorted(self._order, key=self._initiative)

    def _run_final_scoring(self) -> None:
        swamp = self._swamp
        colors = tuple(self._order)
        for color in self._order:
            player = self._players[color]
            total = 0
            for island in swamp.islands():
                total += island.settlements(color) * island.spirit_count
            for card in self._score_cards:
                total += card.score(swamp, color, colors)
            total += sum(
                swamp.space(sid).fish_count for sid in swamp.settlements_of(color)
            )
            total += player.mana
            total += player.gold // GOLD_VP_DIVISOR
            self.award(color, total)

    def _notify_scores(self) -> None:
        for color, player in self._players.items():
            self._scores._notify((color, player.score))

    def _capture(self) -> GameSnapshot:
        return (
            self._swamp._capture(),
            {color: player._capture() for color, player in self._players.items()},
            self._bank._capture(),
            self._cursor,
        )

    def _restore(self, snapshot: GameSnapshot) -> None:
        self._swamp._restore(snapshot[0])
        for color, state in snapshot[1].items():
            self._players[color]._restore(state)
        self._bank._restore(snapshot[2])
        self._cursor = snapshot[3]
