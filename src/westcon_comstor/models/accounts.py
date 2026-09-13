"""Models for the URUP Account Detail and Account Search APIs."""

from __future__ import annotations

from typing import List, Optional, Union

from pydantic import AliasChoices, Field, field_validator

from .common import WestconModel

# ---------------------------------------------------------------------------
# Account Detail (MT_AccountDetail_S_Req / MT_AccountDetail_S_Resp)
# ---------------------------------------------------------------------------


class CustomerDetails(WestconModel):
    name: Optional[str] = None
    name2: Optional[str] = None
    name3: Optional[str] = None
    name4: Optional[str] = None
    street: Optional[str] = None
    street2: Optional[str] = None
    street3: Optional[str] = None
    street4: Optional[str] = None
    street5: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None
    region: Optional[str] = None
    country_key: Optional[str] = None


class ContactDetails(WestconModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = Field(default=None, alias="eMail")
    phone: Optional[str] = None


class AccountDetailResult(WestconModel):
    """Inner payload of ``MT_AccountDetail_S_Resp``."""

    customer_details: Optional[CustomerDetails] = None
    # Documented as an object but returned as a list in the example; accept both.
    contact_details: Union[List[ContactDetails], ContactDetails, None] = None


# ---------------------------------------------------------------------------
# Account Search (MT_AccountSearch_S_Req / MT_AccountSearch_S_Resp)
# ---------------------------------------------------------------------------


class AccountSummary(WestconModel):
    customer: Optional[str] = None
    country: Optional[str] = None
    name1: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    region: Optional[str] = None


class AccountSearchResult(WestconModel):
    """Inner payload of ``MT_AccountSearch_S_Resp``.

    The documented key is ``totalCount``/``customerDetails`` but the example uses
    ``TotalCount``/``CustomerDetails``; both casings are accepted.
    """

    total_count: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("totalCount", "TotalCount")
    )
    customer_details: List[AccountSummary] = Field(
        default=[], validation_alias=AliasChoices("customerDetails", "CustomerDetails")
    )

    @field_validator("total_count", mode="before")
    @classmethod
    def _coerce_total_count(cls, value: object) -> object:
        # Documented as a string but sometimes returned as an integer.
        return str(value) if isinstance(value, int) else value
