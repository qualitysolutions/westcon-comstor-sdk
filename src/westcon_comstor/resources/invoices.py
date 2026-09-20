"""Open Invoice List resource."""

from __future__ import annotations

from .. import _endpoints as ep
from ..models.invoices import InvoiceDetailResult, InvoiceListResult
from ._base import AsyncResource, SyncResource


class InvoicesResource(SyncResource):
    def list(
        self,
        *,
        start_date: str,
        end_date: str | None = None,
        partner_key: str | None = None,
    ) -> InvoiceListResult:
        """List open (unpaid) invoices between ``start_date`` and ``end_date``.

        Dates are ``YYYYMMDD`` strings. ``end_date`` is optional.
        """
        payload = ep.build_open_invoice_list(self._partner_key(partner_key), start_date, end_date)
        raw = self._t.request("POST", ep.PATH_OPEN_INVOICE_LIST, json=payload)
        return ep.parse_open_invoice_list(raw)

    def detail(self, *, invoice_number: str, partner_key: str | None = None) -> InvoiceDetailResult:
        """Header + line detail for a single invoice (partial data; no PDF)."""
        payload = ep.build_invoice_detail(self._partner_key(partner_key), invoice_number)
        raw = self._t.request("POST", ep.PATH_INVOICE_DETAIL, json=payload)
        return ep.parse_invoice_detail(raw)


class AsyncInvoicesResource(AsyncResource):
    async def list(
        self,
        *,
        start_date: str,
        end_date: str | None = None,
        partner_key: str | None = None,
    ) -> InvoiceListResult:
        payload = ep.build_open_invoice_list(self._partner_key(partner_key), start_date, end_date)
        raw = await self._t.request("POST", ep.PATH_OPEN_INVOICE_LIST, json=payload)
        return ep.parse_open_invoice_list(raw)

    async def detail(self, *, invoice_number: str, partner_key: str | None = None) -> InvoiceDetailResult:
        payload = ep.build_invoice_detail(self._partner_key(partner_key), invoice_number)
        raw = await self._t.request("POST", ep.PATH_INVOICE_DETAIL, json=payload)
        return ep.parse_invoice_detail(raw)
