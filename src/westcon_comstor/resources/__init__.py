"""Resource namespaces exposed on the clients."""

from __future__ import annotations

from .accounts import AccountsResource, AsyncAccountsResource
from .fx import AsyncFxResource, FxResource
from .invoices import AsyncInvoicesResource, InvoicesResource
from .misc import AemResource, AsyncAemResource
from .orders import AsyncOrdersResource, OrdersResource
from .products import AsyncProductsResource, ProductsResource
from .quoting import AsyncQuotesResource, QuotesResource
from .shipping import AsyncShippingResource, ShippingResource

__all__ = [
    "InvoicesResource",
    "AsyncInvoicesResource",
    "OrdersResource",
    "AsyncOrdersResource",
    "ProductsResource",
    "AsyncProductsResource",
    "QuotesResource",
    "AsyncQuotesResource",
    "ShippingResource",
    "AsyncShippingResource",
    "AccountsResource",
    "AsyncAccountsResource",
    "AemResource",
    "AsyncAemResource",
    "FxResource",
    "AsyncFxResource",
]
