"""Tests for the additive Quote conveniences: VRF field names, vendor deal id, expiry."""

from datetime import date

from westcon_comstor.models.quoting import QuoteData


def test_vrf_lines_populate_with_field_name_and_vendor_deal_id():
    qd = QuoteData.model_validate({
        "entries": [{
            "VRFLines": [
                {"fieldName": "VRF_MAGICKEY", "value": "Q14366868636-000"},
                {"fieldName": "VRF_VENDOR_QUOTE_NUMBER", "value": "86351633"},
            ],
        }],
    })
    e = qd.entries[0]
    assert len(e.vrf_lines) == 2                       # VRFLines (irregular caps) now maps
    assert e.vrf_lines[1].field_name == "VRF_VENDOR_QUOTE_NUMBER"
    assert e.vendor_deal_id == "86351633"              # matched by field name, not position


def test_vendor_deal_id_none_without_the_field():
    qd = QuoteData.model_validate({"entries": [{"VRFLines": [{"fieldName": "VRF_MAGICKEY", "value": "Q1"}]}]})
    assert qd.entries[0].vendor_deal_id is None


def test_quote_expiry_parsing_and_is_expired():
    past = QuoteData.model_validate({"quoteInformation": {"expireDate": "01/01/2020"}})
    assert past.expiry == date(2020, 1, 1) and past.is_expired is True
    future = QuoteData.model_validate({"quoteInformation": {"expireDate": "31/12/2999"}})
    assert future.is_expired is False
    absent = QuoteData.model_validate({})
    assert absent.expiry is None and absent.is_expired is None
    # Raw expire_date is preserved (not omitted).
    assert past.quote_information.expire_date == "01/01/2020"


def test_quote_dates_parse_to_date():
    from datetime import date
    from westcon_comstor.models.quoting import QuoteData, parse_comstor_date
    qd = QuoteData.model_validate({
        "createdDate": "31/07/2026",
        "quoteInformation": {"expireDate": "07/08/2026", "startDate": "18/09/2026"},
    })
    assert qd.created == date(2026, 7, 31)          # DD/MM/YYYY, not MM/DD
    assert qd.created.isoformat() == "2026-07-31"
    assert qd.expiry == date(2026, 8, 7)
    assert qd.start == date(2026, 9, 18)
    # helper handles other formats + blanks
    assert parse_comstor_date("10/22/2026", "%m/%d/%Y") == date(2026, 10, 22)  # VRF licence date
    assert parse_comstor_date("20210604", "%Y%m%d") == date(2021, 6, 4)        # event date
    assert parse_comstor_date("") is None and parse_comstor_date("bad") is None
