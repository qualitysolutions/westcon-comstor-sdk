"""Quoting resource: Get Quote."""

from __future__ import annotations

from .. import _endpoints as ep
from ..models.quoting import GetQuoteResult
from ._base import AsyncResource, SyncResource


class QuotesResource(SyncResource):
    def get(
        self,
        *,
        quote_id: str,
        reseller_id: str,
        version: str = "",
        partner_key: str | None = None,
    ) -> GetQuoteResult:
        """Retrieve a quote by 1View quote id and version.

        ``version`` empty string means the latest version. ``quote_id`` is the id from
        the Event Listener ``QUOTE_CREATED`` / ``QUOTE_REVISED`` event.
        """
        payload = ep.build_get_quote(
            self._partner_key(partner_key), reseller_id, quote_id, version
        )
        raw = self._t.request("POST", ep.PATH_GET_QUOTE, json=payload)
        return ep.parse_get_quote(raw)


class AsyncQuotesResource(AsyncResource):
    async def get(
        self,
        *,
        quote_id: str,
        reseller_id: str,
        version: str = "",
        partner_key: str | None = None,
    ) -> GetQuoteResult:
        payload = ep.build_get_quote(
            self._partner_key(partner_key), reseller_id, quote_id, version
        )
        raw = await self._t.request("POST", ep.PATH_GET_QUOTE, json=payload)
        return ep.parse_get_quote(raw)
