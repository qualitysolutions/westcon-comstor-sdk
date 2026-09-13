# Phase 2 — PartnerView — hand-off notes

PartnerView is a large API on the same gateway (`https://api.westconcomstor.com`). We are
**sourcing its OpenAPI / Swagger (or Postman) definition from Westcon** rather than
hand-scraping the portal — the portal's OpenAPI export only returns complete paths for
`availability`, and its per-operation data endpoints are not scriptable from the browser.

## Interim: call PartnerView today via the generic escape hatch

Until typed wrappers land, any PartnerView endpoint can be called with:

```python
result = client.request(
    "GET",
    "westconb2brestwebservices/v2/{baseSiteId}/pc/masterData/countries".format(baseSiteId="..."),
    params={"isoCode": "GB,AU"},
)
```

`client.request(method, path, *, json, params, headers, authenticated=True)` returns the
parsed JSON. Pass `authenticated=False` to skip the OAuth2 bearer if an endpoint uses only
its own auth. Extra `headers=` are merged over the defaults.

## PartnerView (50+ operations) — "Commerce Webservices Version 2" (SAP Commerce / Hybris)

Base: `https://api.westconcomstor.com/westconb2brestwebservices/v2/{baseSiteId}/pc/...`
Uses REST path/template + query params (not only POST-JSON). Responses use 200/401/403/404.

Operation groups observed: Westcon Master Data; Access members; Account search; Address /
Address Book (create/validate/search); Cart (add products, check incompletion, create RFQ,
place order, search contact, clean SO); Contact Master; Contact-us form; Finance (dispute,
AR lines, quotation, account transactions); Customer Onboard (questions, language/country,
states, history, validate, zipcode, media, prospect address validation, Synnex redirection);
downloadAvailability / downloadQuote; dashboards / dimensions / business-unit hierarchy /
employee details / never-bounce email; ... (list is truncated by "Show more" in the portal).

Sample — Get country MasterData:
- `GET /westconb2brestwebservices/v2/{baseSiteId}/pc/masterData/countries?fields=&isoCode=GB,AU`
- Params: baseSiteId (path)*, fields (query), isoCode (query).
- 200 `WestconPCCountriesWsDTO`: countries[]/country of WestconPCCountryWsDTO
  {addressParameters[]{display,mandatory,name}, countryCode, countrySalesOrg,
  excludeL2AddressValidation(bool), excludedforFullValidationOfAddress(bool), isocode,
  linkedToSalesOrg, name, states[] of RegionData{countryIso, isocode, isocodeShort, name}},
  phoneCodes[] of CountryCodeData{countryCode, name, selectedCountry(bool)}.
- Auth: Commerce Webservices OAuth Bearer (confirm scopes/headers from the spec).

## When the spec arrives

1. Drop the OpenAPI/Swagger files under `docs/specs/`.
2. Prefer generating models with `datamodel-code-generator` (pydantic v2) into
   `models/partnerview.py`, then hand-write thin resource wrappers mirroring the Phase 1
   pattern (`resources/`), reusing `_transport`.
3. Confirm the auth model (Commerce Webservices OAuth Bearer + any required headers) and
   wire it into the transport if it differs from the transactional-API flow.
