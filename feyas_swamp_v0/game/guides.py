from dataclasses import dataclass
from typing import Final, Protocol

from .core import ClanColor, GuideKind, Resource


@dataclass(frozen=True, slots=True)
class GuideCard:
    kind: GuideKind
    initiative: int
    settlement_value: int
    sailing_range: int


class GuideView(Protocol):
    @property
    def kind(self) -> GuideKind: ...
    @property
    def initiative(self) -> int: ...
    @property
    def settlement_value(self) -> int: ...
    @property
    def sailing_range(self) -> int: ...


class AbilityContext(Protocol):
    def award(self, color: ClanColor, points: int) -> None: ...
    def gain(self, color: ClanColor, resource: Resource, amount: int) -> None: ...
    def add_neutral(self, color: ClanColor, count: int) -> None: ...
    def advance_sailing(self, color: ClanColor) -> None: ...
    def temple_count(self, color: ClanColor) -> int: ...
    def islands_led(self, color: ClanColor) -> int: ...
    def celebrate_best(self, color: ClanColor) -> None: ...


class GuideAbility:
    __slots__ = ()

    def on_income(self, context: AbilityContext, color: ClanColor) -> None:
        return None

    def on_pass(self, context: AbilityContext, color: ClanColor) -> None:
        return None

    @property
    def fishing_bonus(self) -> int:
        return 0

    @property
    def build_discount(self) -> int:
        return 0


class LeaderAbility(GuideAbility):
    __slots__ = ()

    def on_income(self, context: AbilityContext, color: ClanColor) -> None:
        context.gain(color, Resource.GOLD, 2)


class SailorAbility(GuideAbility):
    __slots__ = ()

    def on_income(self, context: AbilityContext, color: ClanColor) -> None:
        context.advance_sailing(color)


class FishermanAbility(GuideAbility):
    __slots__ = ()

    @property
    def fishing_bonus(self) -> int:
        return 1


class MonkAbility(GuideAbility):
    __slots__ = ()

    def on_income(self, context: AbilityContext, color: ClanColor) -> None:
        context.gain(color, Resource.MANA, 2)


class StorytellerAbility(GuideAbility):
    __slots__ = ()

    def on_pass(self, context: AbilityContext, color: ClanColor) -> None:
        context.award(color, 3 * context.temple_count(color))


class BuilderAbility(GuideAbility):
    __slots__ = ()

    @property
    def build_discount(self) -> int:
        return 1


class WarriorAbility(GuideAbility):
    __slots__ = ()

    def on_income(self, context: AbilityContext, color: ClanColor) -> None:
        context.add_neutral(color, 2)


class MerchantAbility(GuideAbility):
    __slots__ = ()

    def on_income(self, context: AbilityContext, color: ClanColor) -> None:
        context.gain(color, Resource.GOLD, 8)


class ArtistAbility(GuideAbility):
    __slots__ = ()

    def on_pass(self, context: AbilityContext, color: ClanColor) -> None:
        context.award(color, 3)
        context.celebrate_best(color)


class WisemanAbility(GuideAbility):
    __slots__ = ()

    def on_pass(self, context: AbilityContext, color: ClanColor) -> None:
        context.award(color, 3 * context.islands_led(color))


GUIDES: Final[dict[GuideKind, GuideCard]] = {
    GuideKind.LEADER: GuideCard(GuideKind.LEADER, 1, 7, 5),
    GuideKind.SAILOR: GuideCard(GuideKind.SAILOR, 2, 6, 5),
    GuideKind.FISHERMAN: GuideCard(GuideKind.FISHERMAN, 3, 5, 4),
    GuideKind.MONK: GuideCard(GuideKind.MONK, 4, 4, 4),
    GuideKind.STORYTELLER: GuideCard(GuideKind.STORYTELLER, 5, 3, 3),
    GuideKind.BUILDER: GuideCard(GuideKind.BUILDER, 6, 3, 3),
    GuideKind.WARRIOR: GuideCard(GuideKind.WARRIOR, 7, 3, 2),
    GuideKind.MERCHANT: GuideCard(GuideKind.MERCHANT, 8, 2, 2),
    GuideKind.ARTIST: GuideCard(GuideKind.ARTIST, 9, 2, 1),
    GuideKind.WISEMAN: GuideCard(GuideKind.WISEMAN, 10, 1, 1),
}

ABILITIES: Final[dict[GuideKind, GuideAbility]] = {
    GuideKind.LEADER: LeaderAbility(),
    GuideKind.SAILOR: SailorAbility(),
    GuideKind.FISHERMAN: FishermanAbility(),
    GuideKind.MONK: MonkAbility(),
    GuideKind.STORYTELLER: StorytellerAbility(),
    GuideKind.BUILDER: BuilderAbility(),
    GuideKind.WARRIOR: WarriorAbility(),
    GuideKind.MERCHANT: MerchantAbility(),
    GuideKind.ARTIST: ArtistAbility(),
    GuideKind.WISEMAN: WisemanAbility(),
}


def ability_for(card: GuideCard) -> GuideAbility:
    return ABILITIES[card.kind]
