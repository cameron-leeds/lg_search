"""Look up Rare Carat certificate IDs in Calavera's public search."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode, urljoin

from playwright.async_api import Browser, async_playwright


CALAVERA_ORIGIN = "https://calaveranewyork.com"


@dataclass(frozen=True)
class CalaveraMatch:
    rare_carat_id: str
    rare_carat_url: str
    lg_code: str | None
    calavera_lg_code: str | None
    calavera_search_url: str | None
    calavera_found: bool
    calavera_url: str | None


def calavera_search_url(lg_code: str) -> str:
    """Build Calavera's search URL, converting ``LG_123`` to ``LG123``."""

    return f"{CALAVERA_ORIGIN}/search?{urlencode({'q': lg_code.replace('_', '')})}"


async def _find_product_url(browser: Browser, search_url: str) -> str | None:
    """Return the first unique product result link from one Calavera search."""

    page = await browser.new_page()
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)
        # Calavera is a Shopify store; product cards are ordinary product links.
        await page.wait_for_timeout(1_000)
        hrefs = await page.locator('a[href*="/products/"]').evaluate_all(
            "links => links.map(link => link.getAttribute('href'))"
        )
        for href in hrefs:
            if href:
                return urljoin(CALAVERA_ORIGIN, href).split("?")[0]
        return None
    finally:
        await page.close()


async def find_calavera_matches(
    rare_carat_results: list[dict[str, object]], *, headless: bool = True
) -> list[CalaveraMatch]:
    """Search Calavera once for every LG code in a Rare Carat result file."""

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        try:
            matches: list[CalaveraMatch] = []
            for record in rare_carat_results:
                lg_code = record.get("lg_code")
                if not isinstance(lg_code, str) or not lg_code:
                    matches.append(
                        CalaveraMatch(
                            rare_carat_id=str(record["rare_carat_id"]),
                            rare_carat_url=str(record["rare_carat_url"]),
                            lg_code=None,
                            calavera_lg_code=None,
                            calavera_search_url=None,
                            calavera_found=False,
                            calavera_url=None,
                        )
                    )
                    continue

                normalized_code = lg_code.replace("_", "")
                search_url = calavera_search_url(lg_code)
                product_url = await _find_product_url(browser, search_url)
                matches.append(
                    CalaveraMatch(
                        rare_carat_id=str(record["rare_carat_id"]),
                        rare_carat_url=str(record["rare_carat_url"]),
                        lg_code=lg_code,
                        calavera_lg_code=normalized_code,
                        calavera_search_url=search_url,
                        calavera_found=product_url is not None,
                        calavera_url=product_url,
                    )
                )
            return matches
        finally:
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Find Rare Carat LG codes on Calavera.")
    parser.add_argument("--input", type=Path, default=Path("rare_carat_lg_codes.json"))
    parser.add_argument("--output", type=Path, default=Path("calavera_matches.json"))
    parser.add_argument("--headed", action="store_true", help="Show Chromium while searches run.")
    args = parser.parse_args()

    records = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("The input file must contain a JSON list of Rare Carat results.")
    matches = asyncio.run(find_calavera_matches(records, headless=not args.headed))
    args.output.write_text(json.dumps([asdict(match) for match in matches], indent=2) + "\n", encoding="utf-8")
    found = sum(match.calavera_found for match in matches)
    print(f"Saved {len(matches)} lookups ({found} Calavera matches) to {args.output}")


if __name__ == "__main__":
    main()
