"""Print Comstor's implied FX rates using the SDK's ``client.fx`` tool.

Comstor has no exchange-rate endpoint, but its pricing engine converts a product's base
price into whatever ``currency`` you request. ``client.fx`` prices the same product(s) in
two currencies and divides the returned list prices to get the effective rate Comstor uses.

Read-only: only the Pricing "get" API is called. No quotes/orders are submitted. Credentials
never printed.

Usage:
    # Credentials from WESTCON_* env vars (or a .env file at the repo root).
    python examples/fx_rates.py --country SE PRODUCT1 [PRODUCT2 ...]
    python examples/fx_rates.py --from EUR USD --to SEK --country SE PRODUCT1 PRODUCT2
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from westcon_comstor import Config, WestconComstorClient


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive Comstor implied FX rates via Pricing API")
    parser.add_argument("products", nargs="+", help="One or more product numbers to price")
    parser.add_argument("--country", default="SE", help="countryCode for the pricing request")
    parser.add_argument("--from", dest="bases", nargs="+", default=["EUR", "USD"],
                        help="Base currencies to convert FROM")
    parser.add_argument("--to", dest="quote", default="SEK", help="Target currency")
    parser.add_argument("--customer", action="store_true",
                        help="Use customerPrice instead of listPrice")
    args = parser.parse_args()

    _load_dotenv()
    try:
        config = Config.from_env()
    except Exception as exc:  # ConfigurationError: missing WESTCON_* vars
        print(f"Missing/invalid credentials: {exc}", file=sys.stderr)
        print("Set WESTCON_CLIENT_ID / _SECRET / _RESOURCE / _SUBSCRIPTION_KEY / _PARTNER_KEY "
              "(env or .env).", file=sys.stderr)
        return 2

    price_field = "customer" if args.customer else "list"
    with WestconComstorClient(config) as client:
        results = client.fx.rates(
            bases=args.bases, quote=args.quote, products=args.products,
            country=args.country, price_field=price_field,
        )

    for r in results:
        print(f"\n=== {r.base_currency}->{r.quote_currency} "
              f"(country={r.country}, {r.price_field} price) ===")
        for s in r.samples:
            print(f"  {s.product_number:<24} {s.base_price:>12,.2f} {r.base_currency}"
                  f"  ->  {s.quote_price:>12,.2f} {r.quote_currency}   rate={s.rate:.4f}")
        for skipped in r.skipped:
            print(f"  {skipped:<24} skipped (no comparable price)")
        if r.rate is not None:
            print(f"  -> implied {r.base_currency}->{r.quote_currency}: median={r.rate:.4f}  "
                  f"(mean={r.mean:.4f}, n={r.sample_count}, spread={r.spread:.2%})")
        else:
            print(f"  -> no comparable prices to derive {r.base_currency}->{r.quote_currency}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
