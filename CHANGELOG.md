# Changelog

All notable changes to `qls-westcon-comstor` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions are
CalVer-style `YY.M.MICRO`. All model additions are **additive** — `extra="allow"` keeps every
raw field, so a new typed property or alias never drops data.

## [26.9.28.2] - 2026-09-28

### Fixed
- `products.pricing` / `pricing_many` (sync + async) now parse the Pricing API's response for
  **`A03 Vendor Obsolete`** products. For those, Comstor sends otherwise valid JSON with an
  **empty value** (`"listPrice" : ,`), which made the whole body invalid JSON, so 26.9.28.1
  raised `APIError("... non-JSON body")` for any request containing such a SKU. Empty values are
  now repaired to `null`: the obsolete product comes back as a normal row (`list_price=None`,
  `error=A03 "Vendor Obsolete"`) and **every other product in the same request** is returned too,
  with no per-product retries (verified live 2026-09-28: 12 SKUs incl. 3 obsolete -> 12 rows in
  2 requests). Unrepairable text bodies still raise `APIError`.

### Corrected
- 26.9.28.1 described these SKUs (`MV2-HW`, `IOTOC-1101-C`, `PWR-C1-715WAC`) as returning a
  "whitespace-only" body. That was a misdiagnosis from inspecting only the body's leading
  whitespace; the real body is the malformed JSON above. The whitespace-only handling and the
  empty-chunk retry from 26.9.28.1 remain as defensive fallbacks.

## [26.9.28.1] - 2026-09-28

### Fixed
- `products.pricing` / `products.availability` (sync + async) no longer crash on a
  **whitespace-only HTTP 200 body**. The live Pricing API returns such a body for some SKUs
  (verified 2026-09-28 with `MV2-HW`; also seen for `IOTOC-1101-C`, `PWR-C1-715WAC`), which used
  to surface as a pydantic `ValidationError`. It now parses to zero results (`[]`). Any other
  non-JSON body raises `APIError("... returned a non-JSON body: ...")` instead of a
  `ValidationError`.
- `products.pricing_many` (sync + async): such a poison SKU blanks the response for **every**
  product in its request, so a chunk of several products that returns no rows is now retried
  one product per request. One bad SKU no longer sinks its neighbours (12 products with one
  poison SKU -> 11 results). Cost: at most `chunk_size` extra requests per blanked chunk (429s
  are retried by the transport as before). Errors (5xx, timeouts, auth) still propagate and are
  **not** fanned out per product.

## [26.9.28] - 2026-09-28

### Fixed
- `products.pricing_many` (sync + async) now defaults to **10 products per request**
  (`PRICING_CHUNK_SIZE`), down from 40. The Pricing API returns at most 10 products per request
  and **silently drops the rest** with no error (verified live 2026-09-28: 12 sent -> 10
  returned), so with the old default every product past the 10th in each chunk went missing.
  Do not pass a `chunk_size` above 10.

### Changed
- `products.availability_many` (sync + async) also defaults to 10 (`AVAILABILITY_CHUNK_SIZE`).
  Availability returned 12/12 live, but its cap is unverified, so it uses the known-safe value.
- `DEFAULT_CHUNK_SIZE` is kept as a backwards-compatible alias and is now 10.

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

[26.9.28.2]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.28.2
[26.9.28.1]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.28.1
[26.9.28]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.28
[26.9.19.1]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.19.1
[26.9.19]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.19
[26.9.18.1]: https://github.com/qualitysolutions/westcon-comstor-sdk/releases/tag/26.9.18.1
