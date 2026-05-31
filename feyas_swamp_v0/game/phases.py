from abc import ABC, abstractmethod

from .core import Phase


class PhaseState(ABC):
    @property
    @abstractmethod
    def phase(self) -> Phase: ...

    @property
    def allows_setup(self) -> bool:
        return False

    @property
    def allows_turn(self) -> bool:
        return False


class SetupPhase(PhaseState):
    @property
    def phase(self) -> Phase:
        return Phase.SETUP

    @property
    def allows_setup(self) -> bool:
        return True


class TurnsPhase(PhaseState):
    @property
    def phase(self) -> Phase:
        return Phase.TURNS

    @property
    def allows_turn(self) -> bool:
        return True


class GameOverState(PhaseState):
    @property
    def phase(self) -> Phase:
        return Phase.OVER
