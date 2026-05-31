"""Utilities for the marketplace package."""

from collections.abc import Callable, Generator, Hashable
from contextlib import contextmanager
from functools import wraps
from typing import Concatenate, Literal, ParamSpec, Self, TypeVar

# TypeVar: a generic type variable, matching a single type
# ParamSpec: a generic function signature type variable, matching a full signature
# Concatenate: use to compose function signatures involving ParamSpec

P = ParamSpec("P")
R = TypeVar("R")
PerishableT = TypeVar("PerishableT", bound="Perishable")
LockableT = TypeVar("LockableT", bound="Lockable")


class StaleError(Exception):
    """Raised when an operation is attempted on a stale object."""

    __slots__ = ()

    def __init__(self, message: str = "operation on a stale object") -> None:
        Exception.__init__(self, message)


class Perishable:
    """
    Mixin for objects that can become stale;
    methods decorated with :meth:`not_stale` raise
    :class:`StaleError` once the object is stale.
    """

    __slots__ = ("__is_stale",)
    # Mixin: no __weakref__ in slots (would force the slot onto extenders).

    __is_stale: Literal[True]

    # No constructor is needed (mixins shouldn't have them for ergonomic optimality):
    # either __is_stale is not set, or it is set to True.
    # Note that the agent inferred this from the annotation Literal[True] alone.

    def _make_stale(self) -> None:
        """Mark this object as stale."""
        self.__is_stale = True

    @staticmethod
    def not_stale(
        method: Callable[Concatenate[PerishableT, P], R],
        #       ^^^^^^^^ a function
        #                                            ^ method return
        #                method self ^^^^^^^^^^  ^ method args and kwargs signature
    ) -> Callable[Concatenate[PerishableT, P], R]:
        """Decorator that raises :class:`StaleError` when the decorated method is invoked on a stale object.

        Intended for methods of subclasses of :class:`Perishable`::

            class Foo(Perishable):
                @Perishable.not_stale
                def bar(self) -> ...:
                    ...
        """
        # A typical decorator for functions/methods defines and returns
        # a new function/method with a signture derived from the decorated one.

        @wraps(method)
        # a standard way to carry over docstring, name and some other attributes
        # of the decorated method (otherwise, this is called "wrapper" and it
        # has no docstring nor owner).
        def wrapper(self: PerishableT, /, *args: P.args, **kwargs: P.kwargs) -> R:
            #                         ^ args before this are positional-only
            # 1. Perform stale object check:
            if hasattr(self, "_Perishable__is_stale"):
                raise StaleError()
            # 2. Call the wrapped method on self, args and kwargs:
            return method(self, *args, **kwargs)

        return wrapper
        # Without / separator, Mypy complains:
        # Incompatible return value type (
        #   got "Callable[[Arg(Perishable, 'self'), **P], R]",
        #   expected "Callable[[Perishable, **P], R]"
        # )
        # This is likely because "wrapper" has named arguments: "self".
        # Consider marking them positional-only


class LockedError(Exception):
    """Raised when an operation is attempted on a locked instance."""

    __slots__ = ()

    def __init__(self, message: str = "this instance is locked") -> None:
        Exception.__init__(self, message)


class Lockable(Perishable):
    """
    Mixin for objects that can be temporarily locked;
    methods decorated with :meth:`not_locked` raise :class:`LockedError`
    while the instance is locked.

    Inherits from :class:`Perishable` so a single mixin chain can supply both
    state-tracking slots (Python's slot rules forbid combining two non-empty
    slotted bases via multiple inheritance).
    """

    __slots__ = ("__is_locked",)
    # Note that slots in mixins should (1) be present and (2) not include __weakref__
    # otherwise they're forced onto mixin extenders.

    __is_locked: bool

    def _lock(self) -> None:
        """Lock this instance."""
        self.__is_locked = True

    def _unlock(self) -> None:
        """Unlock this instance."""
        self.__is_locked = False

    @staticmethod
    def not_locked(
        method: Callable[Concatenate[LockableT, P], R],
    ) -> Callable[Concatenate[LockableT, P], R]:
        """Decorator that raises :class:`LockedError` when the decorated method is invoked on a locked instance.

        Intended for methods of subclasses of :class:`Lockable`::

            class Foo(Lockable):
                @Lockable.not_locked
                def bar(self) -> ...:
                    ...
        """

        @wraps(method)
        def wrapper(
            self: LockableT, /, *args: P.args, **kwargs: P.kwargs
        ) -> R:
            if getattr(self, "_Lockable__is_locked", False):
                raise LockedError()
            return method(self, *args, **kwargs)

        return wrapper


class Lock:
    """A lock that can be set or unset, gating calls to decorated functions.

    The :meth:`set` method is a context manager that sets the lock for the duration of the ``with`` block.
    The :meth:`is_set` method is a decorator that raises :class:`TypeError` when the wrapped function is called while the lock is not set.
    """

    __slots__ = (
        "__weakref__",
        "__is_set",
    )

    __is_set: bool

    def __new__(cls) -> Self:
        instance = object.__new__(cls)
        instance.__is_set = False
        return instance

    # Context Mangers are the modern OOP language incarnation
    # of a very important OOP pattern known as RAAI:
    # Resource Acquisition As Initialisation
    # The classic example is with open(...) as file_descr:,
    # and any other contextual resource management requiring cleanup.

    @contextmanager
    def set(self) -> Generator[None]:
        """Set this lock for the duration of the ``with`` block.

        Typical usage, paired with :meth:`is_set` on a gated function::

            _lock = Lock()

            @_lock.is_set
            def make_widget() -> Widget: ...

            with _lock.set():
                widget = make_widget()  # allowed
            make_widget()  # raises TypeError
        """
        if self.__is_set:
            raise ValueError("Nested lock setting is not allowed.")
        self.__is_set = True
        try:
            yield
            # everything before the yield is executed when entiring the block
            # everything after the yield is executed when exiting the block
            # value returned to the yield (here None) is use by with .. as ..:
        finally:
            # This block is exectued even if an exception was raised in the context,
            # which allows for cleanup to be performed.
            # In particular, the lock is not stuck in set mode if exceptions happen.
            self.__is_set = False

    def is_set(self, func: Callable[P, R]) -> Callable[P, R]:
        """Decorator that raises :class:`TypeError` when ``func`` is called while this lock is not set.

        Typical usage as a decorator on a private constructor or function::

            _lock = Lock()

            class Widget:
                @_lock.is_set
                def __new__(cls) -> Self: ...

            with _lock.set():
                widget = Widget()  # allowed
            Widget()  # raises TypeError
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if not self.__is_set:
                raise TypeError(f"{func.__qualname__} is locked")
            return func(*args, **kwargs)

        return wrapper


class WithdrawableStack[T: Hashable]:
    #                    ^^^^^^^^^^ generic type bound = T must be a subtype of Hashable
    # Hashable is a structurally typed interface, just means __hash__ is defined.
    # Hashable = stable item equality
    # The contract for __hash__ is that x == y => hash(x) == hash(y),
    # which wouldn't be true for mutable collections, which are therefore not hashable.
    """A stack of unique hashable items supporting push and pop at the top, plus removal from anywhere.

    The underlying list backs push/pop at the top; a parallel set tracks which items are still live, so removal from anywhere is O(1) and pop lazily skips items that have been withdrawn.
    """

    __slots__ = (
        "__weakref__",
        "__list",
        "__set",
    )

    __list: list[T]
    __set: set[T]  # hash-based collection, requires T to be hashable

    def __new__(cls) -> Self:
        instance = object.__new__(cls)
        instance.__list = []
        instance.__set = set()
        return instance

    def push(self, item: T) -> None:
        """Push an item on top of the stack. Raises :class:`ValueError` if the item is already present."""
        if item in self.__set:
            raise ValueError(f"item {item!r} is already in the stack")
        self.__list.append(item)
        self.__set.add(item)

    def peek(self) -> T:
        """Return the top item without removing it. Raises :class:`IndexError` if the stack is empty."""
        # 1. Clear removed items from top:
        while self.__list and self.__list[-1] not in self.__set:
            self.__list.pop()
        # 2. Perform the actual peek:
        if not self.__list:
            raise IndexError("peek from an empty stack")
        return self.__list[-1]

    def pop(self) -> T:
        """Remove and return the top item. Raises :class:`IndexError` if the stack is empty."""
        # 1. Clear removed items from top:
        while self.__list and self.__list[-1] not in self.__set:
            self.__list.pop()
        # 2. Perform the actual pop:
        if not self.__list:
            raise IndexError("pop from an empty stack")
        item = self.__list.pop()
        self.__set.remove(item)
        return item

    def remove(self, item: T) -> None:
        """Remove an item from anywhere in the stack. Raises :class:`KeyError` if the item is not present."""
        if item not in self.__set:
            raise KeyError(item)
        self.__set.remove(item)

    def __contains__(self, item: object) -> bool:
        return item in self.__set

    def __len__(self) -> int:
        return len(self.__set)
