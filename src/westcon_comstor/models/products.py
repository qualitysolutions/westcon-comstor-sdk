"""Models for the Availability and Pricing APIs."""

from __future__ import annotations

from typing import List, Optional

from pydantic import AliasChoices, Field

from .common import ErrorNumberPair, WestconModel

# ---------------------------------------------------------------------------
# Availability (Availability_Request / Availability_Response)
# ---------------------------------------------------------------------------


class ProductRef(WestconModel):
    """A product reference used in Availability/Pricing requests."""

    product_number: Optional[str] = None
    long_product_number: Optional[str] = None


class StorageLocation(WestconModel):
    # Availability documents PascalCase keys; the example uses camelCase. Accept both.
    plant: Optional[str] = Field(default=None, validation_alias=AliasChoices("Plant", "plant"))
    location_number: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("LocationNumber", "locationNumber")
    )
    available_quantity: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("AvailableQuantity", "availableQuantity")
    )
    lead_time_in_days: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("LeadTimeInDays", "leadTimeInDays")
    )
    po_quantity: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("POQuantity", "pOQuantity", "poQuantity")
    )
    po_date: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("PODate", "pODate", "poDate")
    )


class AvailabilityProduct(WestconModel):
    product_number: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("ProductNumber", "productNumber")
    )
    long_product_number: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("LongProductNumber", "longProductNumber")
    )
    storage_locations: List[StorageLocation] = Field(
        default=[], validation_alias=AliasChoices("storage_locations", "storageLocations")
    )
    error: Optional[ErrorNumberPair] = None


# ---------------------------------------------------------------------------
# Pricing (MT_Pricing_S_Req / MT_Pricing_Resp)
# ---------------------------------------------------------------------------


class PricedProduct(WestconModel):
    product_number: Optional[str] = None
    long_product_number: Optional[str] = None
    list_price: Optional[float] = None
    customer_price: Optional[float] = None
    currency: Optional[str] = None


class PricingResult(WestconModel):
    """One entry of ``MT_Pricing_Resp``."""

    product: Optional[PricedProduct] = None
    error: Optional[ErrorNumberPair] = None
