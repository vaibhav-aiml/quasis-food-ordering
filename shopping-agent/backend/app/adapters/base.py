"""The Store Adapter interface every store integration must satisfy.

A ``typing.Protocol`` — structural typing, no shared base-class
implementation — matching the pattern already established for
``LLMClient`` (Phase 3) and for the same reason: any object with matching
methods satisfies this interface, which is what lets tests build simple
fakes with zero mocking-library involvement and zero inheritance.

Per Phase 0 architecture doc, section 6: composition, not inheritance —
each concrete adapter (Zepto/Blinkit/Instamart, and eventually a real
Appium-backed one per store) implements this protocol independently; none
of them subclass a shared base with default method bodies. Store UIs
differ enough (different locators, different navigation flows) that
sharing implementation would leak store-specific assumptions into a
supposedly-common base.

``@runtime_checkable`` lets tests assert conformance directly via
``isinstance(adapter, StoreAdapter)`` — a genuine, executable check that
an adapter satisfies every required method, not just a type-checker hint.
"""

from typing import Protocol, runtime_checkable

from app.adapters.types import CartActionResult, CheckoutState, SearchQuery
from app.domain.raw_product_result import RawProductResult


@runtime_checkable
class StoreAdapter(Protocol):
    """Every store integration exposes exactly these five operations."""

    def get_store_id(self) -> str:
        """A stable identifier for this store, e.g. ``'zepto'``."""
        ...

    def is_available(self) -> bool:
        """Whether this store can currently be searched/ordered from.

        Mock adapters (Phase 7) always return ``True``. Once real
        automation exists (Phase 8), this would reflect actual
        reachability (e.g. Appium session health) — deliberately not
        implemented that way yet, since guessing at Phase 8's health-check
        design here would mean jumping ahead of that phase's own work.
        """
        ...

    def search(self, query: SearchQuery) -> list[RawProductResult]:
        """Search this store for the requested products.

        Returns raw, unvalidated results — see ``RawProductResult``'s
        docstring for why the fields are intentionally string-typed.
        """
        ...

    def add_to_cart(self, product: RawProductResult) -> CartActionResult:
        """Add a specific product to this store's cart.

        Takes a ``RawProductResult`` (this adapter's own search output)
        for now, since the eventually-correct parameter type (likely
        ``NormalizedProduct`` or ``RankedResult``) doesn't exist until
        Phase 10/11. The interface will need revisiting once those types
        exist — flagged explicitly here rather than guessed at now.
        """
        ...

    def checkout(self) -> CheckoutState:
        """Attempt checkout for whatever is currently in this store's cart."""
        ...
