"""Base model and shared data types used across Westcon-Comstor APIs."""

from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel, to_pascal


def _validation_aliases(field_name: str) -> AliasChoices:
    """Accept both camelCase and PascalCase for a field on input.

    Westcon payloads are inconsistent: the same concept appears as ``openOrderList`` in
    one API's docs and ``OpenOrderList`` in the live response. Accepting both (plus the
    snake_case name via ``populate_by_name``) means we don't silently drop data over a
    capitalised first letter.
    """
    return AliasChoices(to_camel(field_name), to_pascal(field_name))


class WestconModel(BaseModel):
    """Base for all SDK models.

    * The alias generator accepts both ``camelCase`` and ``PascalCase`` JSON keys on
      input, and serialises to ``camelCase``.
    * ``populate_by_name`` lets callers construct models with the snake_case name.
    * ``extra="allow"`` keeps unknown keys, so we never drop data we did not model.

    Fields whose live key is irregular (``eRPOrderNumber``, ``customerPONumber``, ...)
    still override with an explicit ``Field(alias=...)``.
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=_validation_aliases,
            serialization_alias=to_camel,
        ),
        populate_by_name=True,
        extra="allow",
        protected_namespaces=(),
    )


class ErrorPair(WestconModel):
    """Common ``{error, errorDescription}`` error object (order/invoice lists)."""

    error: Optional[str] = None
    error_description: Optional[str] = None


class ErrorNumberPair(WestconModel):
    """Common ``{errorNumber, errorDescription}`` error object (availability/pricing)."""

    error_number: Optional[str] = None
    error_description: Optional[str] = None


class Price(WestconModel):
    """Monetary value as returned by the quoting APIs."""

    currency_iso: Optional[str] = None
    formatted_value: Optional[str] = None
    value: Optional[float] = None
    value_without_currency: Optional[str] = None


class Country(WestconModel):
    isocode: Optional[str] = None
    name: Optional[str] = None


class Region(WestconModel):
    isocode: Optional[str] = None
    isocode_short: Optional[str] = None
    name: Optional[str] = None
    country_iso: Optional[str] = None


class Account(WestconModel):
    """Account/party block used by the quoting APIs."""

    account_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_line3: Optional[str] = None
    address_line4: Optional[str] = None
    locality: Optional[str] = None
    district: Optional[str] = None
    town: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[Country] = None


class Address(WestconModel):
    company_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    formatted_address: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    line4: Optional[str] = None
    phone: Optional[str] = None
    town: Optional[str] = None
    postal_code: Optional[str] = None
    region: Optional[Region] = None
    country: Optional[Country] = None
