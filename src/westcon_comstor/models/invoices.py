"""Models for the Open Invoice List API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import AliasChoices, Field, field_validator

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


class InvoiceLine(WestconModel):
    """A single line of an invoice (``/invoices/invoicedetail``)."""

    item_number: Optional[str] = None
    delivery_number: Optional[str] = None
    tracking_number: Optional[str] = None
    material: Optional[str] = None
    quantity: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    unit_price: Optional[str] = None
    extended_price: Optional[str] = None
    serial_numbers: Optional[str] = None


class InvoiceDetail(WestconModel):
    """Header + line detail for a single invoice (``/invoices/invoicedetail``).

    The API's own description calls this *partial* invoice data (no PDF / not the complete
    record). The published spec types ``invoiceLine`` as a single object, but real invoices
    are multi-line, so we coerce a single object (or null) into a list.
    """

    # NOTE: the live response is PascalCase and flat (see parse_invoice_detail). The base model
    # accepts camelCase + PascalCase automatically; the acronym fields below need explicit
    # AliasChoices because neither to_camel nor to_pascal reproduces their casing.
    westcon_entity: Optional[str] = None
    westcon_vat_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("WestconVATID", "westconVATID"))
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    sales_order_number: Optional[str] = None
    #: Present in the live response though absent from the spec; links the invoice to its order.
    erp_order_number: Optional[str] = Field(default=None, validation_alias=AliasChoices("ERPOrderNumber", "eRPOrderNumber"))
    currency: Optional[str] = None
    customer_po_number: Optional[str] = Field(default=None, validation_alias=AliasChoices("CustomerPONumber", "customerPONumber"))
    payment_terms: Optional[str] = None
    invoice_due_date: Optional[str] = None
    delivery_method: Optional[str] = None
    total_insurance: Optional[str] = None
    total_freight: Optional[str] = None
    total_rebate: Optional[str] = None
    total_chemical_fee: Optional[str] = None
    documentation_charges: Optional[str] = None
    certificate_of_origin: Optional[str] = None
    saso_charges: Optional[str] = Field(default=None, validation_alias=AliasChoices("SASOCharges", "sASOCharges"))
    total_vat: Optional[str] = Field(default=None, validation_alias=AliasChoices("TotalVAT", "totalVAT"))
    grand_total: Optional[str] = None
    total_price: Optional[str] = None
    total_transaction_fees: Optional[str] = None
    invoice_line: List[InvoiceLine] = []

    @field_validator("invoice_line", mode="before")
    @classmethod
    def _coerce_lines(cls, v):
        if v is None:
            return []
        if isinstance(v, dict):  # spec types a single object; real invoices are multi-line
            return [v]
        return v


class InvoiceDetailResult(WestconModel):
    """Inner payload of ``mT_InvoiceLine_S_Resp`` / ``InvoiceLine_Response``."""

    invoice: Optional[InvoiceDetail] = None
    error: Optional[ErrorPair] = None
