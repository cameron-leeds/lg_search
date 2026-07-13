"""Collect IGI lab-report codes for diamonds returned by a Rare Carat search.

Rare Carat renders the search results in the browser, so this module uses
Playwright rather than trying to guess an internal API.  It only reads public
pages and deliberately visits the detail pages at a modest rate.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError, async_playwright


DEFAULT_SEARCH_URL = (
    "https://www.rarecarat.com/diamond-search/"
    "c1da7094-3c13-4a3f-8dc6-6ac2a9924047?shape=round,oval"
)
DIAMOND_PATH = re.compile(r"^/diamond/(\d+)(?:/|$)")
LG_CODE = re.compile(r"[?&]r=(LG_\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class RareCaratDiamond:
    """A Rare Carat listing and the certificate number used for matching."""

    rare_carat_id: str
    rare_carat_url: str
    lg_code: str | None


async def _scroll_for_diamond_urls(page: Page, limit: int) -> list[str]:
    """Scroll the result list until ``limit`` unique public diamond URLs appear."""

    urls: dict[str, None] = {}
    unchanged_rounds = 0

    for _ in range(80):
        hrefs = await page.locator('a[href*="/diamond/"]').evaluate_all(
            "links => links.map(link => link.getAttribute('href'))"
        )
        for href in hrefs:
            if not href:
                continue
            absolute_url = urljoin(page.url, href).split("?")[0]
            if DIAMOND_PATH.match(absolute_url.removeprefix("https://www.rarecarat.com")):
                urls.setdefault(absolute_url, None)
                if len(urls) >= limit:
                    return list(urls)

        old_height = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1_000)
        new_height = await page.evaluate("document.body.scrollHeight")
        unchanged_rounds = unchanged_rounds + 1 if new_height == old_height else 0
        if unchanged_rounds >= 3:
            break

    return list(urls)


async def _wait_for_diamond_results(page: Page, debug_dir: Path | None) -> None:
    """Wait for result links, retaining useful evidence if the site shows another page."""

    try:
        # Search cards can initially be attached inside a hidden loading container.
        # Waiting for ``visible`` causes a false timeout in that state.
        await page.wait_for_selector('a[href*="/diamond/"]', state="attached", timeout=45_000)
    except PlaywrightTimeoutError as error:
        title = await page.title()
        if debug_dir:
            debug_dir.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=debug_dir / "rare_carat_search_failure.png", full_page=True)
            (debug_dir / "rare_carat_search_failure.html").write_text(
                await page.content(), encoding="utf-8"
            )
        saved = f" Review {debug_dir} for a screenshot and HTML capture." if debug_dir else ""
        raise RuntimeError(
            f"Rare Carat returned no diamond links after 45 seconds (title: {title!r}; URL: {page.url})."
            " It may be showing a consent, verification, or error page." + saved
        ) from error


async def _extract_lg_code(browser: Browser, diamond_url: str) -> RareCaratDiamond:
    """Open one diamond page and get the ``LG_`` code from its IGI link."""

    page = await browser.new_page()
    try:
        await page.goto(diamond_url, wait_until="domcontentloaded", timeout=45_000)
        # The certificate section can be hydrated after the initial HTML.
        try:
            await page.wait_for_selector('a[href*="igi.org/reports/verify-your-report"]', timeout=12_000)
        except PlaywrightTimeoutError:
            pass
        match = LG_CODE.search(await page.content())
        diamond_id = DIAMOND_PATH.search(page.url.removeprefix("https://www.rarecarat.com"))
        if not diamond_id:
            raise ValueError(f"Unexpected Rare Carat diamond URL: {page.url}")
        return RareCaratDiamond(diamond_id.group(1), diamond_url, match.group(1).upper() if match else None)
    finally:
        await page.close()


async def collect_lg_codes(
    search_url: str = DEFAULT_SEARCH_URL,
    limit: int = 100,
    *,
    headless: bool = True,
    debug_dir: Path | None = Path("debug"),
) -> list[RareCaratDiamond]:
    """Return up to ``limit`` top search results, including their IGI ``LG_`` code.

    Results with a missing code are retained so a UI or caller can flag them
    instead of silently losing a listing.
    """

    if limit < 1:
        raise ValueError("limit must be at least 1")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        try:
            search_page = await browser.new_page()
            await search_page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)
            await _wait_for_diamond_results(search_page, debug_dir)
            diamond_urls = await _scroll_for_diamond_urls(search_page, limit)
            await search_page.close()

            # Keeping this sequential is polite to the site and makes failures easier to retry.
            return [await _extract_lg_code(browser, url) for url in diamond_urls[:limit]]
        finally:
            await browser.close()


def write_results(results: Iterable[RareCaratDiamond], output: Path) -> None:
    """Write results as JSON or CSV, selected from the output filename suffix."""

    records = [asdict(result) for result in results]
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".csv":
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["rare_carat_id", "rare_carat_url", "lg_code"])
            writer.writeheader()
            writer.writerows(records)
    else:
        output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Rare Carat diamond IGI LG codes.")
    parser.add_argument("--search-url", default=DEFAULT_SEARCH_URL)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("rare_carat_lg_codes.json"))
    parser.add_argument("--headed", action="store_true", help="Show Chromium while the collector runs.")
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("debug"),
        help="Folder for a screenshot and HTML if search results do not load (default: debug).",
    )
    args = parser.parse_args()
    results = asyncio.run(
        collect_lg_codes(args.search_url, args.limit, headless=not args.headed, debug_dir=args.debug_dir)
    )
    write_results(results, args.output)
    found = sum(result.lg_code is not None for result in results)
    print(f"Saved {len(results)} listings ({found} LG codes) to {args.output}")


if __name__ == "__main__":
    main()
