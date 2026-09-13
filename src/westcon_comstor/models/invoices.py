"""Models for the Open Invoice List API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from .common import ErrorPair, WestconModel


class Invoice(WestconModel):
    billing_document: Optional[str] = None
    customer_order_number: Optional[str] = None
    # Westcon spells this "eRPOrderNumber", which to_camel would not produce.
    erp_order_number: Optional[str] = Field(default=None, alias="eRPOrderNumber")
    payer: Optional[str] = None
    billing_date: Optional[str] = None
    total_value: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    payment_terms: Optional[str] = None
    due_date: Optional[str] = None


class InvoiceListResult(WestconModel):
    """Inner payload of ``MT_InvoiceList_S_Resp``."""

    invoice: List[Invoice] = []
    error: Optional[ErrorPair] = None
