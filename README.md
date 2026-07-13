# lg_search

This starts from a Rare Carat diamond search, gets the first 100 listings, and
extracts each public IGI certificate identifier (`LG_...`). Those identifiers
are the stable values to look up at Calavera and Aurelinne.

## Rare Carat collector

Install the dependency and Chromium once:

```powershell
py -m pip install -r requirements.txt
py -m playwright install chromium
```

Then collect the top 100 results from the configured search:

```powershell
py main.py --output rare_carat_lg_codes.json
```

The output contains `rare_carat_id`, its detail-page URL, and `lg_code`. A
missing `lg_code` is retained as `null` for review. Use `--output results.csv`
to write CSV instead, or pass a different `--search-url` and `--limit`.

If it reports that no diamond links loaded, it saves `debug/rare_carat_search_failure.png`
and `.html`. Run in a visible browser to inspect and handle any normal consent
prompt:

```powershell
py main.py --headed --limit 5
```

## Calavera lookup

Use the Rare Carat output to search Calavera by certificate number. The script
automatically converts `LG_811684624` to Calavera's `LG811684624` search term
and saves whether a product was found and its product URL.

```powershell
py calavera/search.py --input rare_carat_lg_codes.json --output calavera_matches.json
```

ultimately rare carat is the winner, but want to get the best diamond by finding a matching LG number from the other 2

Original search on rare carat - https://www.rarecarat.com/diamond-search/c1da7094-3c13-4a3f-8dc6-6ac2a9924047?shape=round,oval

Oval - https://www.rarecarat.com/diamond-search/5ab45692-b99c-40a4-97f3-5ee6a92d0873?shape=oval
Round - https://www.rarecarat.com/diamond-search/15376876-7977-4b55-a76e-6f14b38e3161?shape=round

Criteria: 
Round Diamond Cheat Sheet
Use these exact settings to get a perfectly proportioned, incredibly fiery round diamond.

Core Filters
Carat: 2.00 to 3.00

Color: D or E (Icy white)

Clarity: VS1 or VVS2 (100% eye-clean)

Fluorescence: None

Cut: Rare Carat Ideal

Polish & Symmetry: Excellent

Advanced Filters
Table: 55% to 57%

Depth: 61% to 62.5%

Crown Angle: 34° to 35°

Pavilion Angle: 40.6° to 41.0°

Girdle: Thin, Med, or Sli. Thick

🥚 Oval Diamond Cheat Sheet
Since ovals don't have an official "Cut" grade, these exact proportions are crucial to ensure a beautiful shape and minimize the dark "bowtie" effect.

Core Filters
Carat: 2.00 to 3.00

Color: D or E (Icy white)

Clarity: VS1 or VVS2 (100% eye-clean)

Fluorescence: None

Polish & Symmetry: Excellent

Advanced Filters
L/W Ratio: 1.40 to 1.45 (The ideal classic oval silhouette)

Table: 56% to 60%

Depth: 60% to 62%

Girdle: Thin, Med, or Sli. Thick

🔍 Final Inspection Tip: When viewing the 360° video of your top choices, check the grading report. If it's a CVD diamond, make sure it doesn't look blurry or grainy. If it's an HPHT diamond, make sure it doesn't have a faint blue tint.

lookups on the other 2 sites

https://aurelinne.com/pages/lab-grown - this one is trickier as it's all in the UI
https://calaveranewyork.com/search?q=LG768694303&options%5Bprefix%5D=last - this one is easy as we can just replace the search

Here is a scenario for rarecarat.com

https://aurelinne.com/pages/lab-grown?id=b935142a-1806-4974-aaa7-30ff67d469dd&stoneType=diamond

This diamond for $434

https://www.rarecarat.com/diamond/147879647/2.21ct-f-vvs2-rare-carat-ideal-round-lab-grown-diamond?ref=back&ts=Search&cs=1

Same diamond at rarecarat.com. open chat and give them both links and ask for them to price match.then give them the link for the setting you want.

https://www.rarecarat.com/setting/170-Presentation-6-Prong-Solitaire-Engagement-Ring-Solitaire/1833983

18k gold 6 prong setting for 502.

Total ring will be 936 plus tax. Free shipping. The diamond alone was twice that price originally on rarecarat.com!

Hope this helps.
