"""URUP account resources: Account Detail and Account Search."""

from __future__ import annotations

from .. import _endpoints as ep
from ..models.accounts import AccountDetailResult, AccountSearchResult
from ._base import AsyncResource, SyncResource


class AccountsResource(SyncResource):
    def detail(
        self,
        *,
        customer: str | None = None,
        partner_key: str | None = None,
    ) -> AccountDetailResult:
        """Get customer + contact details for a customer number."""
        payload = ep.build_account_detail(self._partner_key(partner_key), customer)
        raw = self._t.request("POST", ep.PATH_ACCOUNT_DETAIL, json=payload)
        return ep.parse_account_detail(raw)

    def search(
        self,
        *,
        name: str | None = None,
        customer: str | None = None,
        country: str | None = None,
        partner_key: str | None = None,
    ) -> AccountSearchResult:
        """Search customer accounts by name / customer number / country."""
        payload = ep.build_account_search(self._partner_key(partner_key), name, customer, country)
        raw = self._t.request("POST", ep.PATH_ACCOUNT_SEARCH, json=payload)
        return ep.parse_account_search(raw)


class AsyncAccountsResource(AsyncResource):
    async def detail(
        self,
        *,
        customer: str | None = None,
        partner_key: str | None = None,
    ) -> AccountDetailResult:
        payload = ep.build_account_detail(self._partner_key(partner_key), customer)
        raw = await self._t.request("POST", ep.PATH_ACCOUNT_DETAIL, json=payload)
        return ep.parse_account_detail(raw)

    async def search(
        self,
        *,
        name: str | None = None,
        customer: str | None = None,
        country: str | None = None,
        partner_key: str | None = None,
    ) -> AccountSearchResult:
        payload = ep.build_account_search(self._partner_key(partner_key), name, customer, country)
        raw = await self._t.request("POST", ep.PATH_ACCOUNT_SEARCH, json=payload)
        return ep.parse_account_search(raw)
