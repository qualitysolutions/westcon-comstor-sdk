"""Open Invoice List resource."""

from __future__ import annotations

from .. import _endpoints as ep
from ..models.invoices import InvoiceListResult
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
