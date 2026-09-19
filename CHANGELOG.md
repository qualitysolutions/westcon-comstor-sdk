# Changelog

All notable changes to `qls-westcon-comstor` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are
CalVer-style `YY.M.MICRO`. All model additions are **additive** — `extra="allow"` keeps every
raw field, so a new typed property or alias never drops data.

## [26.9.19.1] - 2026-09-19

### Added
- `to_comstor_date(raw, dayfirst=True)` — auto-detects Comstor's three date shapes (ISO
  `YYYY-MM-DD`, compact `YYYYMMDD`, slash `D/M/YYYY`), uses the ">12" rule to fix slash
  day/month order, and only falls back to the `dayfirst` hint when a value is genuinely
  ambiguous. Unlike `dateutil.parser` it never applies `dayfirst` to ISO/compact dates and
  never fuzzy-fills partial dates; unrecognised input returns `None`. Exported from
  `westcon_comstor.models`.
- `QuoteData.created` / `QuoteData.start` and `QuoteInformation.start` parsed-date properties.
- `QuoteEntry.lic_start` / `QuoteEntry.lic_end` (VRF licence dates, month-first),
  `QuoteEntry.contract_start` / `QuoteEntry.contract_end`, and a generic
  `QuoteEntry.vrf(field_name)` accessor.

### Changed
- The quote date properties (`created` / `start` / `expiry`) now parse via `to_comstor_date`.
- `parse_comstor_date(raw, fmt)` remains as the explicit-format escape hatch.

## [26.9.19] - 2026-09-19

### Added
- `StorageLocation.available_on_date` on the Product Availability response (`AvailableOnDate` /
  `availableOnDate`). Per the API guide it is a snapshot date ("in most cases the current
  date"), not a restock/ETA date — prefer `lead_time_in_days` for ETAs.
- Quote conveniences: `QuoteEntry.vendor_deal_id` (the VRF value whose `field_name` is
  `VRF_VENDOR_QUOTE_NUMBER`, matched by name not position); `QuoteInformation` with a parsed
  `expiry`; and `QuoteData.expiry` / `QuoteData.is_expired`.

### Fixed
- `QuoteEntry.vrf_lines` / `vrf_quantities` now accept the live `VRFLines` / `VRFQuantities`
  key casing, so they actually populate (previously only reachable via `model_extra`).

## [26.9.18.1] - 2026-09-18

### Added
- Initial release: synchronous and asynchronous clients, typed pydantic v2 models, OAuth2
  client-credentials auth, and a typed error hierarchy. MIT-licensed.

### Fixed
- `tenant_id` defaults to Westcon-Comstor's Azure AD tenant (the API's OAuth authority, shared
  by all partners) and is overridable via `WESTCON_TENANT_ID`. (26.9.18 wrongly required it
  after mislabelling it the caller's tenant.)

[26.9.19.1]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.19.1
[26.9.19]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.19
[26.9.18.1]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.18.1
