"""Models for the Get Quote API.

The Get Quote response (``GetQuoteResponse.quoteData``) is very large. The structured,
frequently-used pieces are fully typed here; every other documented scalar is preserved
via ``extra="allow"`` on :class:`~westcon_comstor.models.common.WestconModel`, so no data
is lost even where it is not explicitly declared.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, Field

from .common import Account, Address, Price, WestconModel

#: The VRF fieldName that carries the Cisco vendor deal id.
VENDOR_DEAL_ID_FIELD = "VRF_VENDOR_QUOTE_NUMBER"

#: Comstor quote header dates (created/expire/start) come as DD/MM/YYYY.
QUOTE_DATE_FORMAT = "%d/%m/%Y"


def parse_comstor_date(raw: Optional[str], fmt: str = QUOTE_DATE_FORMAT) -> Optional[date]:
    """Parse a Comstor date string in ``fmt`` (default ``DD/MM/YYYY``) to a ``date``.

    Returns ``None`` for a blank or unparseable value. Comstor mixes date formats across
    fields, so pass the right ``fmt`` per field (e.g. ``"%m/%d/%Y"`` for VRF licence dates,
    ``"%Y%m%d"`` for Event Listener dates). Use ``.isoformat()`` on the result for ISO output.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, fmt).date()
    except ValueError:
        return None


class NameValue(WestconModel):
    field_name: Optional[str] = None
    value: Optional[str] = None


class DeliveryMode(WestconModel):
    code: Optional[str] = None
    delivery_cost: Optional[Price] = None
    name: Optional[str] = None


class PeriodicBillingEntry(WestconModel):
    billing_date: Optional[str] = None
    billing_value: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class QuoteProduct(WestconModel):
    code: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[str] = None
    name: Optional[str] = None
    included_in_the_box: Optional[bool] = None
    included_with_line: Optional[str] = None
    original_sku: Optional[str] = None
    spared_out: Optional[bool] = None
    vendor_qt_line_number: Optional[str] = None


class QuoteEntry(WestconModel):
    availability_in_selected_plant: Optional[float] = Field(
        default=None, alias="availabilityinSelectedPlant"
    )
    currency_symbol: Optional[str] = None
    customer_line_number: Optional[str] = None
    customer_part_number: Optional[str] = None
    display_entry_number: Optional[float] = None
    #: Live key is ``VRFLines`` (irregular caps); accept the doc casing too.
    vrf_lines: List[NameValue] = Field(
        default=[], validation_alias=AliasChoices("VRFLines", "vRFLines", "vrfLines"))
    vrf_quantities: List[NameValue] = Field(
        default=[], validation_alias=AliasChoices("VRFQuantities", "vRFQuantities", "vrfQuantities"))
    chemical_tax: Optional[Price] = None
    contract_start_date: Optional[str] = None
    contract_end_date: Optional[str] = None
    duration: Optional[str] = None
    estimated_freight: Optional[float] = None
    extended_list_price: Optional[Price] = None
    extended_price: Optional[Price] = None
    group_description: Optional[str] = None
    group_id: Optional[str] = None
    group_id_and_description: Optional[str] = None
    import_duty_absolute: Optional[Price] = None
    import_duty_percentage: Optional[float] = None
    inbound_duty: Optional[Price] = None
    inbound_duty_percentage: Optional[float] = None
    list_price: Optional[Price] = None
    listing_fees: Optional[Price] = None
    periodic_billing: List[PeriodicBillingEntry] = []
    list_price_in_quote_currency: Optional[Price] = None
    pricing_condition_label: Optional[str] = None
    product: Optional[QuoteProduct] = None
    quantity: Optional[float] = None
    reseller_price: Optional[Price] = None
    total_incl_vat: Optional[float] = Field(default=None, alias="totalInclVAT")
    total_price: Optional[Price] = None
    type: Optional[str] = None
    vat_absolute: Optional[Price] = None
    vat_percentage: Optional[float] = None
    vendor_currency: Optional[str] = None
    vendor_name: Optional[str] = None
    volume: Optional[str] = None
    weight: Optional[str] = None

    @property
    def vendor_deal_id(self) -> Optional[str]:
        """The Cisco deal id: the VRF line named ``VRF_VENDOR_QUOTE_NUMBER`` (labels are stable,
        their position is not). ``None`` when the line has no such VRF field."""
        for nv in self.vrf_lines:
            if nv.field_name == VENDOR_DEAL_ID_FIELD:
                return nv.value
        return None


class QuoteComment(WestconModel):
    comment: Optional[str] = None
    date: Optional[str] = None
    user: Optional[str] = None


class QuoteUser(WestconModel):
    name: Optional[str] = None
    uid: Optional[str] = None


class QuoteInformation(WestconModel):
    """The ``quoteInformation`` block. Raw fields are kept as returned; ``expiry`` parses the
    ``expire_date`` (``DD/MM/YYYY``) into a :class:`datetime.date`."""

    created_by_email: Optional[str] = None
    created_by_phone: Optional[str] = None
    currency: Optional[List[str]] = None
    expire_date: Optional[str] = None          # raw, e.g. "25/09/2026"
    expire_date_in_yyyy: Optional[str] = None
    start_date: Optional[str] = None
    start_date_in_yyyy: Optional[str] = None

    @property
    def expiry(self) -> Optional[date]:
        """``expire_date`` parsed to a date (ISO via ``.isoformat()``), or None."""
        return parse_comstor_date(self.expire_date)

    @property
    def start(self) -> Optional[date]:
        """``start_date`` parsed to a date, or None."""
        return parse_comstor_date(self.start_date)


class QuoteData(WestconModel):
    """The ``quoteData`` block. Structured fields are typed; other documented scalars
    (opportunity*, region, salesOrg*, totals, dates, flags, etc.) are preserved via
    ``extra="allow"`` and remain accessible as attributes / in ``model_extra``.
    """

    code: Optional[str] = None
    delivery_address: Optional[Address] = None
    delivery_cost: Optional[Price] = None
    delivery_mode: Optional[DeliveryMode] = None
    entries: List[QuoteEntry] = []
    sub_total: Optional[Price] = None
    total_items: Optional[float] = None
    total_price: Optional[Price] = None
    total_price_with_tax: Optional[Price] = None
    total_tax: Optional[Price] = None
    user: Optional[QuoteUser] = None
    bill_to_account: Optional[Account] = None
    ship_to_account: Optional[Account] = None
    sold_to_account: Optional[Account] = None
    end_user_account: Optional[Account] = None
    end_user_address: Optional[Address] = None
    b2b_sales_org: Optional[Dict[str, Any]] = Field(default=None, alias="b2BSalesOrg")
    total_chemical_tax: Optional[Price] = None
    total_list_price: Optional[Price] = None
    total_listing_fees: Optional[Price] = None
    total_reseller_price: Optional[Price] = None
    comments: List[QuoteComment] = []
    currency: Optional[str] = None
    quote_code: Optional[str] = None
    version_id: Optional[str] = None
    note: Optional[str] = None
    created_by: Optional[str] = None
    created_date: Optional[str] = None
    region: Optional[str] = None
    quote_information: Optional[QuoteInformation] = None

    @property
    def expiry(self) -> Optional[date]:
        """The quote's parsed expiry date (from ``quote_information``), or None."""
        return self.quote_information.expiry if self.quote_information else None

    @property
    def is_expired(self) -> Optional[bool]:
        """Whether the quote's expiry date is in the past; None when the date is unknown."""
        d = self.expiry
        return (d < date.today()) if d is not None else None

    @property
    def created(self) -> Optional[date]:
        """The quote's ``created_date`` (DD/MM/YYYY) parsed to a date, or None."""
        return parse_comstor_date(self.created_date)

    @property
    def start(self) -> Optional[date]:
        """The quote's start date (from ``quote_information``), or None."""
        return self.quote_information.start if self.quote_information else None


class GetQuoteResult(WestconModel):
    """Full ``GetQuoteResponse`` body."""

    message: Optional[str] = None
    quote_data: Optional[QuoteData] = None
    success: Optional[bool] = None
