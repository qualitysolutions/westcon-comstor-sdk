"""Typed models for Westcon-Comstor API requests and responses."""

from __future__ import annotations

from .accounts import (
    AccountDetailResult,
    AccountSearchResult,
    AccountSummary,
    ContactDetails,
    CustomerDetails,
)
from .common import (
    Account,
    Address,
    Country,
    ErrorNumberPair,
    ErrorPair,
    Price,
    Region,
    WestconModel,
)
from .fx import ImpliedRate, ProductRate
from .invoices import Invoice, InvoiceListResult
from .orders import (
    OpenOrder,
    OpenOrderListResult,
    OrderInvoice,
    OrderNumberQuery,
    OrderStatusLine,
    OrderStatusValueLine,
    OrderStatusValueResult,
    OrderValue,
)
from .products import (
    AvailabilityProduct,
    PricedProduct,
    PricingResult,
    ProductRef,
    StorageLocation,
)
from .quoting import (
    DeliveryMode,
    GetQuoteResult,
    PeriodicBillingEntry,
    QuoteComment,
    QuoteData,
    QuoteEntry,
    QuoteProduct,
    QuoteUser,
)
from .shipping import (
    OrderSerialNumber,
    OrderStatusDetail,
    OrderTrackingDetail,
    OrderTrackResult,
    OrderVRFData,
    ServiceEvent,
    ShipmentTrackingResult,
    TrackingImage,
)

__all__ = [
    "WestconModel",
    "Account",
    "Address",
    "Country",
    "Region",
    "Price",
    "ErrorPair",
    "ErrorNumberPair",
    # fx
    "ImpliedRate",
    "ProductRate",
    # invoices
    "Invoice",
    "InvoiceListResult",
    # orders
    "OpenOrder",
    "OpenOrderListResult",
    "OrderInvoice",
    "OrderStatusLine",
    "OrderNumberQuery",
    "OrderStatusValueLine",
    "OrderStatusValueResult",
    "OrderValue",
    # products
    "ProductRef",
    "StorageLocation",
    "AvailabilityProduct",
    "PricedProduct",
    "PricingResult",
    # quoting
    "GetQuoteResult",
    "QuoteData",
    "QuoteEntry",
    "QuoteProduct",
    "DeliveryMode",
    "PeriodicBillingEntry",
    "QuoteComment",
    "QuoteUser",
    # shipping
    "ShipmentTrackingResult",
    "TrackingImage",
    "ServiceEvent",
    "OrderTrackResult",
    "OrderStatusDetail",
    "OrderTrackingDetail",
    "OrderSerialNumber",
    "OrderVRFData",
    # accounts
    "AccountDetailResult",
    "AccountSearchResult",
    "AccountSummary",
    "CustomerDetails",
    "ContactDetails",
]
