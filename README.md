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

ultimately rare carat is the winner, but want to get the best diamond by finding a matching LG number from the other 2

Original search on rare carat - https://www.rarecarat.com/diamond-search/c1da7094-3c13-4a3f-8dc6-6ac2a9924047?shape=round,oval

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
