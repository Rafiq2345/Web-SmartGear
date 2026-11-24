# Amazon Auto-Price Updater — SmartGearPick

Keeps the Amazon prices on smartgearpick.com fresh automatically, using
Amazon's **official Creators API** (the successor to the deprecated PA-API
5.0). Built 24 Nov 2026. **NOT live yet** — see "Enablement" below. Nothing
here touches the live site and no credentials exist anywhere in this folder.

## Status (24 Nov 2026)

| Item | State |
|---|---|
| ASIN map | Built from the live site (61 pages) — `asin-map.json` |
| Updater script | Written + tested in mock mode — `price_sync.py` |
| GitHub Action | Staged here only, **not pushed** — `price-sync.yml` |
| Test proof | `test-output/` (before/after diff, mock run log) |
| Credentials | **None exist.** Blocked on 10 qualifying sales in 30 days (account has 0). |
| Live site | Untouched. Nothing has been pushed to GitHub. |

## How it works

```
1. asin-map.json      — which product lives on which page, and which
                        structured price field(s) it feeds
2. price_sync.py      — hourly: fetches live prices from the Creators API,
                        rewrites ONLY changed structured price fields
3. price-sync.yml     — GitHub Action: runs the script hourly, commits +
                        pushes only when a price actually changed
```

### What gets updated — and what never does

- **Updated:** `.product-price-est` divs and comparison-table price cells
  that hold a **single** price (164 fields today).
- **Never touched:** prose paragraphs (1,193 `$` mentions stay manual),
  price **ranges** ("$649–$799", 76 fields), tier labels ("Top Pick",
  8 fields), manufacturer-store prices, and any field whose recorded text
  no longer matches the page (the script skips it and logs it).
- **Safety:** every rewrite is anchored to the exact current text of the
  field (block id for price-est divs, row label for table cells). If the
  page changed since the map was built, the field is skipped, not guessed.
- **Stamp:** every changed page gets one HTML comment before `</body>`:
  `<!-- smartgearpick price-sync: prices checked <UTC time> (Amazon Creators API) -->`.
  Only one stamp per page — it is refreshed on each run.
- **Log:** each run writes a JSON log (changed ASINs old → new, skipped
  items with reasons, API errors, pages changed).

### The map — key numbers (live site, 24 Nov 2026)

- **61 pages** fetched from the live sitemap; **167 Amazon links** total.
- **Only 23 are `/dp/` links → 12 distinct ASINs** (3 pages). The other
  **144 are search links** (`/s?k=...`, no ASIN) — those products need ASIN
  resolution before they can auto-update.
- **134 products, 248 structured fields:** 164 auto-updatable (single
  price), 76 ranges (manual), 8 tier labels (no price).
- **Only 5 of the 12 known ASINs have auto-updatable fields (8 fields
  total):** AirTag 2 (2), Echo Dot 5th Gen (1), Fitbit Inspire 3 (2),
  Anker 622 (1), JBL Tune 520BT (2). The other 7 sit behind range/tier
  price-est divs (all 5 NC-headphone ASINs are tier labels).
- **104 products need ASIN resolution** (74 of them have auto-updatable
  fields — the priority queue). **18 products have structured fields but
  no Amazon link at all** (manufacturer/other prices — the updater skips
  them entirely). **43 Amazon links** sit in prose/Sources sections, not
  in any product block.
- **0 products have their price only in prose** — every product with a
  price has at least one structured field.

### The 12 known ASINs

| ASIN | Product |
|---|---|
| B0GPT1FJBD | Sony WH-1000XM6 |
| B0FDKR293G | Bose QuietComfort Ultra (2nd Gen) |
| B0CQ2TBSPV | Sennheiser Momentum 4 |
| B0DWT9XPLS | JBL Tour One M3 |
| B0B5VHRX7F | Anker Soundcore Space Q45 |
| B0GJTFXNRX | Apple AirTag 2 |
| B09B8V1LZ3 | Amazon Echo Dot (5th Gen) |
| B0B5F9SZW7 | Fitbit Inspire 3 |
| B07CMS5Q6P | Logitech G305 |
| B0B4667885 | Anker 622 Magnetic Battery |
| B0C1HGKNG7 | JBL Tune 520BT |
| B0C683F516 | Arlo Video Doorbell 2K (2nd Gen) |

## The API (researched from Amazon's official docs, 24 Nov 2026)

- **Token:** `POST https://api.amazon.com/auth/o2/token` with JSON
  `{grant_type: "client_credentials", client_id, client_secret,
  scope: "creatorsapi::default"}` → `{access_token, expires_in: 3600}`
  (1-hour token; the script caches it and refreshes on expiry).
- **Prices:** `POST https://creatorsapi.amazon/catalog/v1/getItems`,
  headers `Authorization: Bearer <token>`,
  `Content-Type: application/json`, `x-marketplace: www.amazon.com`;
  body `{itemIds (max 10), itemIdType: "ASIN",
  marketplace: "www.amazon.com", partnerTag: "smartgearpi0a-20",
  condition: "New", resources: ["itemInfo.title",
  "offersV2.listings.price", "offersV2.listings.isBuyBoxWinner",
  "offersV2.listings.availability", "offersV2.listings.merchantInfo"]}`.
  The script uses the **Buy Box winner** listing only; `price.money`
  is the current price, `price.savingBasis.money` is the list price.
- **ASIN resolution:** `searchItems` returns candidates — the script's
  `--resolve` mode writes them to JSON for **human verification only**;
  it never auto-assigns an ASIN.
- **Limits:** ~1 request/second, 8,640 requests/day, 10 ASINs per call.
  The script batches in 10s with a 1.1s delay and exponential backoff.

## Enablement — exact steps for Rafiq (only when sales qualify)

Do these **after** the account has 10 qualifying sales in the trailing
30 days (access returns automatically ~48h after the new sales ship —
nothing to apply for; the Creators API section simply appears in
Associates Central).

1. **Associates Central** → **Creators API** → create OAuth credentials
   (client ID + client secret). Keep them off chat/email — copy them
   straight into step 2. **Check the credential Version shown in Associates
   Central: new accounts get v3.x, which is what the script uses by default.
   If yours shows v2.x, tell Muse before the first run — the token endpoint
   must be switched via the `AMAZON_TOKEN_URL` repo variable (see "Known
   limitations" below).**
2. **GitHub repo → Settings → Secrets and variables → Actions → New
   repository secret**, add two secrets:
   - `AMAZON_CLIENT_ID`
   - `AMAZON_CLIENT_SECRET`
3. **Place the files in the repo** (from this folder):
   - `price_sync.py` → `scripts/price-updater/price_sync.py`
   - `asin-map.json` → `scripts/price-updater/asin-map.json`
   - `price-sync.yml` → `.github/workflows/price-sync.yml`
   (Push via the GitHub web UI or a normal commit — these are text files.)
4. **Test manually first:** Actions tab → "Amazon price sync" →
   **Run workflow**. Check the run log artifact and the commit it made
   (if any price changed). The workflow only commits when prices changed.
5. **Leave the hourly schedule on.** It runs at the top of every hour
   (UTC). If a run finds no changes, it commits nothing.

> **Do NOT push `price-sync.yml` before step 2.** The workflow has a
> guard that skips the sync when the secrets are missing, so pushing it
> early is harmless — but pointless.

## Limits (honest)

- **Amazon prices only.** Manufacturer-store prices (e.g. "at Roborock's
  US store") and every prose mention stay manual — the script cannot
  verify them and never touches prose.
- **Ranges stay manual.** A field like "$649–$799" cannot be replaced by
  one API price; those 76 fields keep needing the manual Black Friday /
  sale-season checks.
- **1-hour cache rule.** Amazon's developer docs give offers a 1-hour
  TTL (24h max per the IP License). The hourly schedule keeps us inside
  it. **If the schedule is ever relaxed below hourly, every displayed
  price needs a visible "Prices checked <date>" line + disclaimer next
  to it** — the HTML comment stamp alone is not enough.
- **10-in-30 eligibility.** The Creators API is only available to
  Associates accounts with ≥10 qualifying sales in the trailing 30 days.
  If sales drop below that, Amazon can revoke access; the script then
  exits without changing anything and the site keeps its last verified
  prices.
- **No scraping, ever.** Prices come only from the official API. Amazon
  prohibits scraping and blocks it technically.
- **The map is a snapshot (24 Nov 2026).** If a page's structure or a
  product's price-est text changes by hand, re-run `build_asin_map.py`
  (needs `lxml`: `pip install lxml`) and commit the refreshed
  `asin-map.json`. The script's stale-check will skip mismatched fields
  rather than corrupt them, but a stale map means fewer fields update.

## What happens if the API is down

- The script exits **code 2** without writing anything. The workflow
  fails loudly (visible in the Actions tab) while **the site keeps its
  last verified prices** — a stale price is never presented as fresh.
- Transient errors are retried with exponential backoff (up to 3 tries);
  a 401 refreshes the token once and retries.
- Exit codes: `0` = ok (possibly with changes), `1` = config error
  (missing credentials / bad map), `2` = API unavailable (no changes).

## Usage

```bash
# Live sync (needs AMAZON_CLIENT_ID / AMAZON_CLIENT_SECRET in the environment)
python3 price_sync.py --map asin-map.json --repo /path/to/repo --log price-sync-log.json

# Dry run — reports what WOULD change, writes nothing
python3 price_sync.py --map asin-map.json --repo /path/to/repo --dry-run --log dry-run-log.json

# Test mode — mock API responses instead of the live API
python3 price_sync.py --map test-output/test-map.json --repo /tmp/price-test \
    --mock test-output/mock-getitems.json --log test-output/test-run-log.json

# ASIN resolution — writes candidates to JSON for HUMAN verification (never auto-assigns)
python3 price_sync.py --map asin-map.json --repo /path/to/repo --resolve \
    --resolve-out asin-candidates.json
```

The script is **stdlib-only** (no pip installs needed in the Action).

## Test proof (24 Nov 2026, mock mode)

Two fresh copies of the live pages in `/tmp/price-test` (never the live
site), mock getItems responses for 8 mock ASINs
(`test-output/mock-getitems.json`):

- **Roborock S8 MaxV Ultra** mock price $799.99 → **$749.99** (changed):
  both its price-est div and its comparison-table cell rewrote cleanly
  (`~$799.99` → `~$749.99`, qualifier text preserved). One stamp added.
- **Lenovo Yoga 7i** mock price $899.00 = current (unchanged): no change.
- **eufy / Roomba / Swift Go / TUF / MacBook Air M2 / Dreame**: mock prices
  differ, but all their fields are ranges → correctly skipped.
- **Result:** 8 ASINs checked, 2 fields changed on 1 page, 0 skipped,
  0 API errors, 11 fields left manual. Robot page diff = exactly 2
  changed lines + 1 stamp line; laptops page byte-identical.
  Before/after files + run log in `test-output/`.
- Dry run verified separately: reports the same 2 changes, writes nothing.
- No-credentials runs exit cleanly (code 1, "AMAZON_CLIENT_ID /
  AMAZON_CLIENT_SECRET are not set") without touching any file.

Two bugs found and fixed during testing: the stamp regex could not match
its own timestamp (hyphens), which duplicated the stamp — now the stamp
is stripped and re-inserted once per page; and range/tier skips were
silent — now counted as `fields_left_manual` in the log.

## Known limitations

- **Name variants split entries.** The same physical product can appear
  under slightly different names in different guides (e.g. "Acer Swift Go
  14" in best-laptops-for-students vs "Acer Swift Go 14 OLED" in
  best-laptops-under-1000). They become separate map entries and dedupe
  only when both resolve to the same ASIN. Harmless for the sync itself.
- **Search-linked products dominate.** 144 of 167 Amazon links carry no
  ASIN. Until `--resolve` + human verification fills those in, the
  updater can only sync the 8 auto-updatable fields behind the 12 known
  ASINs. The priority queue is the 74 resolution candidates with
  auto-updatable fields (`asin-map-summary.md`).
- **`pages/` is a local snapshot** (24 Nov 2026 fetch, for map-building
  only) — it is NOT part of what gets pushed to the repo. The three
  `.html` files with empty names in `pages/comparisons/`,
  `pages/guides/`, `pages/reviews/` are fetch artifacts of directory
  index URLs.

## Files in this folder

| File | Purpose |
|---|---|
| `asin-map.json` | The map: 134 products → pages → structured fields |
| `asin-map-summary.md` | Human-readable map summary + resolution priority |
| `build_asin_map.py` | Rebuilds the map from the live sitemap (needs `lxml`) |
| `price_sync.py` | The updater (stdlib-only) |
| `price-sync.yml` | GitHub Action (hourly) — staged, do not push yet |
| `sitemap.xml` | Live sitemap snapshot, 24 Nov 2026 |
| `pages/` | Local snapshot of all 61 live pages (map-building input) |
| `test-output/` | Mock responses, test map, before/after pages, run logs |
| `README.md` | This file |
