"""Listings in the marketplace."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Literal,
    Protocol,
    Self,
    TypedDict,
    Unpack,
    cast,
    reveal_type,
)

from .bids import Bids
from .utils import Lockable, Perishable

if TYPE_CHECKING:
    from .users import Bid, Buyer, Seller

# from .utils import Lock
# _lock = Lock()
# ^^^^^^^^^^^^^^ remnant of an ill-fated attempt to gate __new__...

# Typed dictionaries are structurally typed:
# at runtime they are dictionaries, and static typecheckers will recognise
# a dictionary to be of a given TypedDict class if it has the required fields
# with the required types (as far as the typechecker is convinced).
# The total kwarg to the class is used to specify whether the keys
# are by default required (total=True, default) or not required (total=False);
# the Required and NotRequired types from typing can be used key-wise.


class IncompleteListingInfo(TypedDict, total=False):
    """Listing information where some or all fields may be missing."""

    title: str
    description: str
    min_bidding_time: timedelta
    start_price: Decimal


class CompleteListingInfo(TypedDict, total=True):
    """Listing information with all fields populated."""

    title: str
    description: str
    min_bidding_time: timedelta
    start_price: Decimal


type OnActivateCallback = Callable[[ActiveListing], None]
type OnSellCallback = Callable[[SoldListing], None]
type OnCancelCallback = Callable[[CancelledListing], None]

type ListingUID = int
type ListingState = Literal["draft", "active", "sold", "cancelled"]
"""
This means the finite set containing exactly those 4 strings and nothing else.
In typescript you could just take a union of the strings themselves,
but in Python that already had a different meaning.
"""
# The type statement does not allow mutation or re-assignment.
# Note: this is a static typechecking thing, at runtime you can do anything.


class _BaseListing(Lockable, ABC):
    """Abstract base class for all listings, holding identity (uid + seller). Inherits Lockable (which itself inherits Perishable) so a single mixin chain is in play (Python slot rules disallow multiple slotted bases)."""

    __slots__ = (
        "__weakref__",
        "__uid",
        "__seller",
    )

    __uid: ListingUID
    __seller: Seller

    def _init_base(self, uid: ListingUID, seller: Seller) -> None:
        """Initialise the base-listing fields. To be called from subclass :meth:`_new`."""
        self.__uid = uid
        self.__seller = seller

    @property
    def uid(self) -> ListingUID:
        """The unique identifier of this listing within its marketplace."""
        return self.__uid

    @property
    def seller(self) -> Seller:
        """The seller of this listing."""
        return self.__seller

    # How to make an abstract property:
    # 1. Start with a method
    # 2. Wrap it into the abstractmethod decorator (enables ABC bookkeeping)
    # 3. Wrap it into the property decorator
    # It doesn't work the other way: @property does not return a method,
    # so @abstractmethod cannot be applied to the result.
    @property
    @abstractmethod
    def state(self) -> ListingState:
        """The state of this listing."""
        ...

    @property
    @abstractmethod
    def info(self) -> IncompleteListingInfo:
        """A copy of this listing's info (may be incomplete for draft/cancelled listings)."""
        ...

    def clone(self) -> DraftListing:
        """Create a new draft listing for the same seller in the same marketplace, populated with this listing's info."""
        new_draft = self.seller.marketplace.draft_listing(self.seller)
        new_draft.set(**self.info)
        return new_draft


class DraftListing(_BaseListing):
    """A draft listing in the marketplace."""

    __slots__ = (
        "__info",
        "__undo_stack",
        "__on_activate",
        "__on_cancel",
    )

    __info: IncompleteListingInfo
    __undo_stack: list[tuple[frozenset[str], dict[str, object]]]
    __on_activate: list[OnActivateCallback]
    __on_cancel: list[OnCancelCallback]

    # State property is implemented with a narrower output type
    @property
    def state(self) -> Literal["draft"]:
        return "draft"

    # # @_lock.is_set
    # def __new__(cls) -> Self:
    # instance = object.__new__(cls)
    # instance.__info = {}
    # return instance

    def __new__(cls) -> Self:
        raise TypeError("Listings are not constructed directly.")

    # Class methods can be used to implement alternative constructors.
    # (More generally they are the instance methods of the class objects.)
    # They have cls as first argument (like __new__) and can use that
    # class information internally to construct an instance.
    @classmethod
    def _new(cls, uid: ListingUID, seller: Seller) -> Self:
        """Protected constructor, for internal use"""
        instance = object.__new__(cls)
        instance._init_base(uid, seller)
        instance.__info = {}
        instance.__undo_stack = []
        instance.__on_activate = []
        instance.__on_cancel = []
        return instance

    # Memento pattern
    # A pair of methods which allow a snapshot of class state to be:
    # - first, created (here, the info property)
    # - later, restored (here, the set method)

    # Builder pattern
    # An object has its necessary information specified not entirely
    # at contstruction, but possibly at a later stage, possibly in
    # arbitrary order, and then there is some "finalising" method
    # which creates the fully built object.
    # Here implemented by a pair of methods:
    # - set allows you to set listing information, in any order
    # - activate creates the complete object

    @property
    @Perishable.not_stale
    def info(self) -> IncompleteListingInfo:
        """A copy of this draft listing's incomplete info."""
        return self.__info.copy()

    @Perishable.not_stale
    def set(self, **kwargs: Unpack[IncompleteListingInfo]) -> None:
        """Update one or more fields of this draft listing's info.

        Usage with explicit field names::

            draft.set(title="Vintage chair", start_price=Decimal("50.00"))

        Usage with dict unpacking (e.g. to restore from a memento)::

            snapshot = draft.info
            draft.set(**snapshot)
        """
        if "title" in kwargs and len(kwargs["title"]) > 50:
            raise ValueError("title must be at most 50 characters")
        if "description" in kwargs and len(kwargs["description"]) > 500:
            raise ValueError("description must be at most 500 characters")
        if "start_price" in kwargs and kwargs["start_price"] <= Decimal("0"):
            raise ValueError("start_price must be strictly positive")
        if "min_bidding_time" in kwargs and kwargs["min_bidding_time"] <= timedelta(0):
            raise ValueError("min_bidding_time must be strictly positive")
        info_dict = cast(dict[str, object], self.__info)
        touched = frozenset(kwargs.keys())
        previous: dict[str, object] = {
            k: info_dict[k] for k in touched if k in info_dict
        }
        self.__undo_stack.append((touched, previous))
        self.__info.update(kwargs)

    @Perishable.not_stale
    def undo(self) -> None:
        """Revert the most recent :meth:`set` call. Raises :class:`IndexError` if there is nothing to undo."""
        if not self.__undo_stack:
            raise IndexError("nothing to undo")
        touched, previous = self.__undo_stack.pop()
        info_dict = cast(dict[str, object], self.__info)
        for key in touched:
            if key in previous:
                info_dict[key] = previous[key]
            else:
                info_dict.pop(key, None)

    # State pattern
    # Objects change behaviour by changing internal state.
    # - Here, you have to imagine that the "conceptual object" is a listing,
    #   and that the four classes implement its stateful behaviour.
    # - In the model answer, it's genuinely a single instance which changes
    #   an internal state variable and acts based on it.
    # In this design, staging checks are taken care of by the fact that
    # methods are defined on different classes, ** but ** we must have
    # a mechanism to mark instances as stale after the transition has happened.

    @Perishable.not_stale
    @Lockable.not_locked
    def activate(self) -> ActiveListing:
        """Activate this draft listing, transitioning it to active state."""
        info = self.__info
        if len(info) != 4:
            raise ValueError("Cannot activate: all listing info fields must be set")
        complete = cast(CompleteListingInfo, info.copy())
        self._make_stale()
        new_listing = ActiveListing._new(self.uid, self.seller, **complete)
        new_listing._lock()
        for callback in self.__on_activate:
            callback(new_listing)
        new_listing._unlock()
        return new_listing

    @Perishable.not_stale
    @Lockable.not_locked
    def cancel(self) -> CancelledListing:
        """Cancel this draft listing, transitioning it to cancelled state."""
        self._make_stale()
        new_listing = CancelledListing._new(self.uid, self.seller, self.__info.copy())
        new_listing._lock()
        for callback in self.__on_cancel:
            callback(new_listing)
        new_listing._unlock()
        return new_listing

    # Publish-Subscribe Pattern
    # Observers register callbacks via the on_<transition> methods;
    # the corresponding state transition method invokes all registered callbacks,
    # passing the newly-constructed next-state instance. The new instance is
    # locked for the duration of callback dispatch, so callbacks cannot trigger
    # further transitions on it and break event-management flow.

    @Perishable.not_stale
    def on_activate(self, callback: OnActivateCallback) -> None:
        """Register a callback to be invoked when this draft listing is activated."""
        self.__on_activate.append(callback)

    @Perishable.not_stale
    def on_cancel(self, callback: OnCancelCallback) -> None:
        """Register a callback to be invoked when this draft listing is cancelled."""
        self.__on_cancel.append(callback)


class ActiveListing(_BaseListing):
    """An active listing in the marketplace."""

    __slots__ = (
        "__info",
        "__activation_time",
        "__bids",
        "__on_sell",
        "__on_cancel",
    )

    __info: CompleteListingInfo
    __activation_time: datetime
    __bids: Bids
    __on_sell: list[OnSellCallback]
    __on_cancel: list[OnCancelCallback]

    @property
    def state(self) -> Literal["active"]:
        return "active"

    @property
    def info(self) -> IncompleteListingInfo:
        """A copy of this active listing's info."""
        return cast(IncompleteListingInfo, self.__info.copy())

    @property
    def bids(self) -> Bids:
        """The bids placed on this listing."""
        return self.__bids

    # # @_lock.is_set
    # def __new__(cls, **kwargs: Unpack[CompleteListingInfo]) -> Self:
    #     instance = object.__new__(cls)
    #     instance.__info = kwargs
    #     instance.__activation_time = datetime.now()
    #     instance.__bids = Bids()
    #     return instance

    def __new__(cls) -> Self:
        raise TypeError("Listings are not constructed directly.")

    @classmethod
    def _new(
        cls, uid: ListingUID, seller: Seller, **kwargs: Unpack[CompleteListingInfo]
    ) -> Self:
        """Protected constructor, for internal use"""
        instance = object.__new__(
            cls
        )  # the __new__ method of object, not ActiveListing
        instance._init_base(uid, seller)
        instance.__info = kwargs
        instance.__activation_time = datetime.now()
        instance.__bids = Bids()
        instance.__on_sell = []
        instance.__on_cancel = []
        instance.__bids.on_submit(instance._on_bid_submit)
        instance.__bids.on_withdraw(instance._on_bid_withdraw)
        return instance

    # State pattern

    @Perishable.not_stale
    @Lockable.not_locked
    def sell(self) -> SoldListing:
        """Sell this active listing to the highest bidder."""
        if not self.__bids:
            raise ValueError("Cannot sell: no bids present")
        elapsed = datetime.now() - self.__activation_time
        if elapsed < self.__info["min_bidding_time"]:
            raise ValueError("Cannot sell: minimum bidding time has not elapsed")
        top_bid = self.__bids.top
        self.__bids._make_stale()
        self._make_stale()
        new_listing = SoldListing._new(
            self.uid,
            self.seller,
            self.__info.copy(),
            self.__activation_time,
            top_bid.buyer,
            top_bid.amount,
        )
        new_listing._lock()
        for callback in self.__on_sell:
            callback(new_listing)
        new_listing._unlock()
        return new_listing

    @Perishable.not_stale
    @Lockable.not_locked
    def cancel(self) -> CancelledListing:
        """Cancel this active listing, transitioning it to cancelled state."""
        if self.__bids:
            raise ValueError("Cannot cancel: bids are present")
        self.__bids._make_stale()
        self._make_stale()
        new_listing = CancelledListing._new(
            self.uid,
            self.seller,
            cast(IncompleteListingInfo, self.__info.copy()),
        )
        new_listing._lock()
        for callback in self.__on_cancel:
            callback(new_listing)
        new_listing._unlock()
        return new_listing

    # Publish-Subscribe Pattern

    @Perishable.not_stale
    def on_sell(self, callback: OnSellCallback) -> None:
        """Register a callback to be invoked when this active listing is sold."""
        self.__on_sell.append(callback)

    @Perishable.not_stale
    def on_cancel(self, callback: OnCancelCallback) -> None:
        """Register a callback to be invoked when this active listing is cancelled."""
        self.__on_cancel.append(callback)

    # Callbacks to handle bid stack events

    def _on_bid_submit(self, bid: Bid) -> None:
        # For future use.
        pass

    def _on_bid_withdraw(self, bid: Bid) -> None:
        # For future use.
        pass


class SoldListing(_BaseListing):
    """A sold listing in the marketplace."""

    __slots__ = (
        "__info",
        "__activation_time",
        "__buyer",
        "__sold_price",
    )

    __info: CompleteListingInfo
    __activation_time: datetime
    __buyer: Buyer
    __sold_price: Decimal

    @property
    def state(self) -> Literal["sold"]:
        return "sold"

    @property
    def info(self) -> IncompleteListingInfo:
        """A copy of this sold listing's info."""
        return cast(IncompleteListingInfo, self.__info.copy())

    @property
    def buyer(self) -> Buyer:
        """The buyer who won the bidding and bought this listing."""
        return self.__buyer

    @property
    def sold_price(self) -> Decimal:
        """The price at which this listing was sold (the winning bid amount)."""
        return self.__sold_price

    # @_lock.is_set
    # def __new__(
    #     cls,
    #     info: CompleteListingInfo,
    #     activation_time: datetime,
    #     buyer: Buyer,
    #     sold_price: Decimal,
    # ) -> Self:
    #     instance = object.__new__(cls)
    #     instance.__info = info
    #     instance.__activation_time = activation_time
    #     instance.__buyer = buyer
    #     instance.__sold_price = sold_price
    #     return instance

    def __new__(cls) -> Self:
        raise TypeError("Listings are not constructed directly.")

    @classmethod
    def _new(
        cls,
        uid: ListingUID,
        seller: Seller,
        info: CompleteListingInfo,
        activation_time: datetime,
        buyer: Buyer,
        sold_price: Decimal,
    ) -> Self:
        """Protected constructor, for internal use"""
        instance = object.__new__(cls)
        instance._init_base(uid, seller)
        instance.__info = info
        instance.__activation_time = activation_time
        instance.__buyer = buyer
        instance.__sold_price = sold_price
        return instance


class CancelledListing(_BaseListing):
    """A cancelled listing in the marketplace."""

    __slots__ = ("__info",)

    __info: IncompleteListingInfo

    @property
    def state(self) -> Literal["cancelled"]:
        return "cancelled"

    @property
    def info(self) -> IncompleteListingInfo:
        """A copy of this cancelled listing's info (may be incomplete)."""
        return self.__info.copy()

    # @_lock.is_set
    # def __new__(cls, info: IncompleteListingInfo) -> Self:
    # instance = object.__new__(cls)
    # instance.__info = info
    # return instance

    def __new__(cls) -> Self:
        raise TypeError("Listings are not constructed directly.")

    @classmethod
    def _new(cls, uid: ListingUID, seller: Seller, info: IncompleteListingInfo) -> Self:
        """Protected constructor, for internal use"""
        instance = object.__new__(cls)
        instance._init_base(uid, seller)
        instance.__info = info
        return instance


type Listing = DraftListing | ActiveListing | SoldListing | CancelledListing
"""
A tagged union type: a union where the members can be discriminated by the value
of one (or more) properties. Here, the tag property is 'state'.
"""

# Listings can be of one of a finite enumeration of non-overlapping types,
# so a tagged union is the correct pattern to use to define the type
# of a listing with unknown state, such as those returned by Marketplace.listing.


class ListingFolderView(Protocol):
    """Readonly structural view of a :class:`ListingFolder`."""

    @property
    def drafts(self) -> Mapping[ListingUID, DraftListing]: ...

    @property
    def active(self) -> Mapping[ListingUID, ActiveListing]: ...

    @property
    def sold(self) -> Mapping[ListingUID, SoldListing]: ...

    @property
    def cancelled(self) -> Mapping[ListingUID, CancelledListing]: ...

    def get(self, uid: ListingUID) -> Listing: ...


class ListingFolder:
    """A folder of listings, automatically updated as listings transition between states."""

    __slots__ = (
        "__weakref__",
        "__drafts",
        "__active",
        "__sold",
        "__cancelled",
    )

    __drafts: dict[ListingUID, DraftListing]
    __active: dict[ListingUID, ActiveListing]
    __sold: dict[ListingUID, SoldListing]
    __cancelled: dict[ListingUID, CancelledListing]

    def __new__(cls) -> Self:
        instance = object.__new__(cls)
        instance.__drafts = {}
        instance.__active = {}
        instance.__sold = {}
        instance.__cancelled = {}
        return instance

    @property
    def drafts(self) -> Mapping[ListingUID, DraftListing]:
        """Readonly view of the draft listings in this folder."""
        return MappingProxyType(self.__drafts)

    @property
    def active(self) -> Mapping[ListingUID, ActiveListing]:
        """Readonly view of the active listings in this folder."""
        return MappingProxyType(self.__active)

    @property
    def sold(self) -> Mapping[ListingUID, SoldListing]:
        """Readonly view of the sold listings in this folder."""
        return MappingProxyType(self.__sold)

    @property
    def cancelled(self) -> Mapping[ListingUID, CancelledListing]:
        """Readonly view of the cancelled listings in this folder."""
        return MappingProxyType(self.__cancelled)

    def get(self, uid: ListingUID) -> Listing:
        """Return the listing with the given uid, looked up across all four state folders. Raises :class:`KeyError` if no such listing exists."""
        if uid in self.__drafts:
            return self.__drafts[uid]
        if uid in self.__active:
            return self.__active[uid]
        if uid in self.__sold:
            return self.__sold[uid]
        if uid in self.__cancelled:
            return self.__cancelled[uid]
        raise KeyError(uid)

    def add(self, listing: Listing) -> None:
        """Add the listing to the folder for its current state, and register callbacks to track future transitions.

        Raises :class:`ValueError` if a listing with this uid is already in the corresponding folder.
        """
        match listing:
            case DraftListing():
                if listing.uid in self.__drafts:
                    raise ValueError(f"listing {listing.uid} is already in the folder")
                self.__drafts[listing.uid] = listing
                listing.on_activate(self._on_activate)
                listing.on_cancel(self._on_cancel)
            case ActiveListing():
                if listing.uid in self.__active:
                    raise ValueError(f"listing {listing.uid} is already in the folder")
                self.__active[listing.uid] = listing
                listing.on_sell(self._on_sell)
                listing.on_cancel(self._on_cancel)
            case SoldListing():
                if listing.uid in self.__sold:
                    raise ValueError(f"listing {listing.uid} is already in the folder")
                self.__sold[listing.uid] = listing
            case CancelledListing():
                if listing.uid in self.__cancelled:
                    raise ValueError(f"listing {listing.uid} is already in the folder")
                self.__cancelled[listing.uid] = listing

    def _on_activate(self, active: ActiveListing) -> None:
        """Callback: a tracked draft was activated."""
        del self.__drafts[active.uid]
        self.__active[active.uid] = active
        active.on_sell(self._on_sell)
        active.on_cancel(self._on_cancel)

    def _on_sell(self, sold: SoldListing) -> None:
        """Callback: a tracked active listing was sold."""
        del self.__active[sold.uid]
        self.__sold[sold.uid] = sold

    def _on_cancel(self, cancelled: CancelledListing) -> None:
        """Callback: a tracked draft or active listing was cancelled."""
        if cancelled.uid in self.__drafts:
            del self.__drafts[cancelled.uid]
        else:
            del self.__active[cancelled.uid]
        self.__cancelled[cancelled.uid] = cancelled
