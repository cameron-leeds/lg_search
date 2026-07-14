"""Look up Rare Carat certificate IDs using Aurelinne's certificate search."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


AURELINNE_ORIGIN = "https://aurelinne.com"
AURELINNE_SEARCH_API = "https://api.aurelinne.com/search?certificate="


@dataclass(frozen=True)
class AurelinneMatch:
    rare_carat_id: str
    rare_carat_url: str
    lg_code: str | None
    aurelinne_lg_code: str | None
    aurelinne_found: bool
    aurelinne_url: str | None


def aurelinne_lg_code(lg_code: str) -> str:
    """Convert Rare Carat's ``LG_123`` form to Aurelinne's ``LG123`` form."""

    return lg_code.replace("_", "")


def lookup_aurelinne(lg_code: str) -> str | None:
    """Return Aurelinne's diamond URL for one certificate, if it has a match."""

    normalized_code = aurelinne_lg_code(lg_code)
    request = Request(
        AURELINNE_SEARCH_API + quote(normalized_code),
        headers={"Accept": "application/json", "User-Agent": "lg-search/1.0"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as error:
        # Aurelinne's lookup API responds with 400 when a certificate is not
        # in its collection, and 404 when no resource is available.
        if error.code in (400, 404):
            return None
        raise RuntimeError(f"Aurelinne lookup failed for {normalized_code}: HTTP {error.code}") from error

    product_url = payload.get("url") if isinstance(payload, dict) else None
    return urljoin(AURELINNE_ORIGIN, product_url) if isinstance(product_url, str) and product_url else None


def find_aurelinne_matches(rare_carat_results: list[dict[str, object]]) -> list[AurelinneMatch]:
    """Look up every LG code in a Rare Carat collector result file."""

    matches: list[AurelinneMatch] = []
    for record in rare_carat_results:
        lg_code = record.get("lg_code")
        if not isinstance(lg_code, str) or not lg_code:
            matches.append(
                AurelinneMatch(
                    rare_carat_id=str(record["rare_carat_id"]),
                    rare_carat_url=str(record["rare_carat_url"]),
                    lg_code=None,
                    aurelinne_lg_code=None,
                    aurelinne_found=False,
                    aurelinne_url=None,
                )
            )
            continue

        product_url = lookup_aurelinne(lg_code)
        matches.append(
            AurelinneMatch(
                rare_carat_id=str(record["rare_carat_id"]),
                rare_carat_url=str(record["rare_carat_url"]),
                lg_code=lg_code,
                aurelinne_lg_code=aurelinne_lg_code(lg_code),
                aurelinne_found=product_url is not None,
                aurelinne_url=product_url,
            )
        )
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(description="Find Rare Carat LG codes on Aurelinne.")
    parser.add_argument("--input", type=Path, default=Path("rare_carat_lg_codes.json"))
    parser.add_argument("--output", type=Path, default=Path("aurelinne_matches.json"))
    args = parser.parse_args()

    records = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("The input file must contain a JSON list of Rare Carat results.")
    matches = find_aurelinne_matches(records)
    args.output.write_text(json.dumps([asdict(match) for match in matches], indent=2) + "\n", encoding="utf-8")
    found = sum(match.aurelinne_found for match in matches)
    print(f"Saved {len(matches)} lookups ({found} Aurelinne matches) to {args.output}")


if __name__ == "__main__":
    main()
