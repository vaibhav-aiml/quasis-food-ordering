"""Raw, unvalidated product search result straight from a Store Adapter.

Per Phase 0 architecture doc, section 11: deliberately "raw" and
string-typed (``raw_price``, ``raw_eta``, ``raw_quantity`` as ``str``, not
``float``/``int``) because this represents scraped data exactly as a
store adapter observed it — BEFORE any validation or parsing happens.
Turning these strings into real numbers, rejecting malformed values, and
deduplicating is explicitly Phase 9's job (Verification Layer), not this
contract's. Store Adapters (Phase 7 onward) are the only producers of
this type.
"""

from pydantic import BaseModel, Field


class RawProductResult(BaseModel):
    """One product as observed directly from a store's UI (or its mock)."""

    store_id: str = Field(min_length=1)
    raw_title: str = Field(min_length=1)
    raw_price: str = Field(
        min_length=1,
        description="Unparsed price string, e.g. '42.00' — Phase 9 parses this.",
    )
    raw_eta: str = Field(
        min_length=1,
        description="Unparsed delivery-time string, e.g. '15 mins' — Phase 9 parses this.",
    )
    raw_quantity: str = Field(
        min_length=1,
        description="Unparsed quantity/unit string, e.g. '1 kg' — Phase 9 parses this.",
    )
    screenshot_ref: str | None = Field(
        default=None,
        description=(
            "Path to a debug screenshot, if one was captured — see "
            "app.automation.screenshots.capture_screenshot."
        ),
    )
