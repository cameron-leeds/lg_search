"""Find Ritani loose-diamond listings through a Google certificate search."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from playwright.async_api import Browser, Page, async_playwright


GOOGLE_SEARCH_URL = "https://www.google.com/search?"


@dataclass(frozen=True)
class RitaniMatch:
    rare_carat_id: str
    rare_carat_url: str
    lg_code: str | None
    ritani_lg_code: str | None
    google_search_url: str | None
    ritani_found: bool
    ritani_url: str | None


class GoogleVerificationError(RuntimeError):
    """Raised when Google requires human verification before it shows results."""


def ritani_lg_code(lg_code: str) -> str:
    """Convert Rare Carat's ``LG_123`` form to the ``LG123`` web-search term."""

    return lg_code.replace("_", "")


def google_search_url(lg_code: str) -> str:
    """Build the same Google query used for a manual Ritani lookup."""

    return GOOGLE_SEARCH_URL + urlencode({"q": ritani_lg_code(lg_code)})


def _unwrap_google_url(href: str) -> str:
    """Extract an external URL from either a direct or Google redirect link."""

    parsed = urlparse(href)
    if parsed.netloc.endswith("google.com") and parsed.path == "/url":
        return parse_qs(parsed.query).get("q", [href])[0]
    return href


def _is_matching_ritani_product(url: str, normalized_code: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.netloc.lower() in {"ritani.com", "www.ritani.com"}
        and "/products/" in parsed.path
        and normalized_code.lower() in url.lower()
    )


async def _find_ritani_url(
    browser: Browser, lg_code: str, *, wait_for_human_verification: bool
) -> str | None:
    """Search Google and prefer a loose-diamond result over a setting bundle."""

    page: Page = await browser.new_page()
    try:
        search_url = google_search_url(lg_code)
        await page.goto(search_url, wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(1_500)
        body_text = (await page.locator("body").inner_text()).lower()
        if "unusual traffic" in body_text or "verify you are human" in body_text:
            if not wait_for_human_verification:
                raise GoogleVerificationError(
                    "Google requested verification. Re-run with --headed, complete it yourself, then retry."
                )
            print("Google requires verification in the open browser. Waiting up to two minutes for completion...")
            for _ in range(120):
                await page.wait_for_timeout(1_000)
                body_text = (await page.locator("body").inner_text()).lower()
                if "unusual traffic" not in body_text and "verify you are human" not in body_text:
                    break
            else:
                raise GoogleVerificationError("Google verification was not completed within two minutes.")

        normalized_code = ritani_lg_code(lg_code)
        hrefs = await page.locator("a[href]").evaluate_all(
            "links => links.map(link => link.href)"
        )
        candidates = [
            _unwrap_google_url(href)
            for href in hrefs
            if _is_matching_ritani_product(_unwrap_google_url(href), normalized_code)
        ]
        # A ring-builder result has two products joined with an encoded '+'.
        # Prefer the standalone loose-diamond listing when Google returns both.
        return next((url for url in candidates if "%2b" not in url.lower()), candidates[0] if candidates else None)
    finally:
        await page.close()


async def find_ritani_matches(
    rare_carat_results: list[dict[str, object]], *, headless: bool = True
) -> list[RitaniMatch]:
    """Look up every Rare Carat LG code on Ritani via its Google result."""

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        try:
            matches: list[RitaniMatch] = []
            for record in rare_carat_results:
                lg_code = record.get("lg_code")
                if not isinstance(lg_code, str) or not lg_code:
                    matches.append(
                        RitaniMatch(str(record["rare_carat_id"]), str(record["rare_carat_url"]), None, None, None, False, None)
                    )
                    continue

                product_url = await _find_ritani_url(
                    browser, lg_code, wait_for_human_verification=not headless
                )
                matches.append(
                    RitaniMatch(
                        rare_carat_id=str(record["rare_carat_id"]),
                        rare_carat_url=str(record["rare_carat_url"]),
                        lg_code=lg_code,
                        ritani_lg_code=ritani_lg_code(lg_code),
                        google_search_url=google_search_url(lg_code),
                        ritani_found=product_url is not None,
                        ritani_url=product_url,
                    )
                )
                # Avoid rapid requests; Google may otherwise ask for verification.
                await asyncio.sleep(2)
            return matches
        finally:
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Find Rare Carat LG codes on Ritani via Google.")
    parser.add_argument("--input", type=Path, default=Path("rare_carat_lg_codes.json"))
    parser.add_argument("--output", type=Path, default=Path("ritani_matches.json"))
    parser.add_argument("--headed", action="store_true", help="Show Chromium for any required human verification.")
    args = parser.parse_args()

    records = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("The input file must contain a JSON list of Rare Carat results.")
    matches = asyncio.run(find_ritani_matches(records, headless=not args.headed))
    args.output.write_text(json.dumps([asdict(match) for match in matches], indent=2) + "\n", encoding="utf-8")
    found = sum(match.ritani_found for match in matches)
    print(f"Saved {len(matches)} lookups ({found} Ritani matches) to {args.output}")


if __name__ == "__main__":
    main()
