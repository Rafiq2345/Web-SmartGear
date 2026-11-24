#!/usr/bin/env python3
"""SmartGearPick Amazon price sync (Creators API, NOT PA-API v5).

Rewrites ONLY structured price fields (.product-price-est divs and
comparison-table price cells) in the site's HTML, using live prices from
Amazon's Creators API. Prose is never touched. Ranges, tier labels and
fields whose recorded price no longer matches the page are skipped.

API (official docs: affiliate-program.amazon.com/creatorsapi/docs):
  - Token: POST https://api.amazon.com/auth/o2/token
      {"grant_type":"client_credentials","client_id":...,
       "client_secret":...,"scope":"creatorsapi::default"}
      -> {"access_token":..., "expires_in": 3600}
  - Prices: POST https://creatorsapi.amazon/catalog/v1/getItems
      headers: Authorization: Bearer <token>, Content-Type: application/json,
               x-marketplace: www.amazon.com
      body: {"itemIds":[...<=10...], "itemIdType":"ASIN",
             "marketplace":"www.amazon.com", "partnerTag":"smartgearpi0a-20",
             "condition":"New",
             "resources":["itemInfo.title","offersV2.listings.price",
                          "offersV2.listings.isBuyBoxWinner",
                          "offersV2.listings.availability",
                          "offersV2.listings.merchantInfo"]}
      response: {"itemsResult":{"items":[{"asin":...,
        "offersV2":{"listings":[{"isBuyBoxWinner":true,
          "price":{"money":{"amount":59.49,"currency":"USD",
                            "displayAmount":"$59.49"},
                   "savingBasis":{"money":{...list price...}},
                   "savings":{"money":{...},"percentage":...}},
          "availability":{"message":"In Stock"},
          "merchantInfo":{"name":"Amazon.com"}}]}}]},
        "errors":[...]}
  - Price used: the buy-box winner listing's price.money.
    savingBasis.money is the list price (when Amazon returns one).

Credentials come ONLY from env vars AMAZON_CLIENT_ID / AMAZON_CLIENT_SECRET
(GitHub repo secrets in the Action). They are never written to disk or logs.

Modes:
  --sync            normal run (default): fetch live prices, rewrite fields.
  --dry-run         report what would change, write nothing.
  --mock FILE       use mock getItems responses from FILE instead of the API
                    (test mode; no credentials needed).
  --resolve         resolve missing ASINs via searchItems for products that
                    have an Amazon search link; writes candidates to
                    --resolve-out for HUMAN verification. Never auto-assigns.

Exit codes: 0 ok (changed or nothing to change), 1 config/usage error,
2 API unavailable (no file was changed).

Cache rule: offers TTL is 1 hour per Amazon's developer docs (24h max per
the IP License). This script is run hourly by the GitHub Action, so prices
are never more than ~1h old. If a run is ever relaxed below hourly, a
visible "Prices checked <date>" line + disclaimer must be shown next to
prices (see README.md). Each changed page gets an HTML comment stamp with
the check time.
"""

import argparse
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

TOKEN_URL = os.environ.get("AMAZON_TOKEN_URL",
                          "https://api.amazon.com/auth/o2/token")
# Default = v3.x (Login with Amazon) NA endpoint. New Associates accounts get
# v3.x credentials. If Associates Central ever issues v2.x (Cognito) credentials,
# set AMAZON_TOKEN_URL to the Cognito endpoint instead, e.g.
# https://creatorsapi.auth.us-east-1.amazoncognito.com/oauth2/token
# (and the Authorization header then needs a ", Version 2.1" suffix).
API_BASE = "https://creatorsapi.amazon"
MARKETPLACE = "www.amazon.com"
PARTNER_TAG = "smartgearpi0a-20"
RESOURCES = [
    "itemInfo.title",
    "offersV2.listings.price",
    "offersV2.listings.isBuyBoxWinner",
    "offersV2.listings.availability",
    "offersV2.listings.merchantInfo",
]
BATCH_SIZE = 10
RATE_DELAY = 1.1  # ~1 req/sec
MONEY_RE = re.compile(r"\$[\d,]+(?:\.\d{1,2})?")
STAMP_RE = re.compile(r"<!-- smartgearpick price-sync: prices checked .*?-->\n?")


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_ws(s):
    return " ".join((s or "").split())


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")


def parse_amount(text):
    m = MONEY_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace("$", "").replace(",", ""))
    except ValueError:
        return None


def replace_first_amount(text, new_display):
    m = MONEY_RE.search(text or "")
    if not m:
        return None
    return text[:m.start()] + new_display + text[m.end():]


# ---------------------------------------------------------------- API client

class ApiUnavailable(Exception):
    pass


class CreatorsApi:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._token_expires = 0.0

    def _http(self, url, payload, headers, timeout=30):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:500]
            raise ApiUnavailable(f"HTTP {e.code} from {url}: {body}")

    def token(self):
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        out = self._http(TOKEN_URL, {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "creatorsapi::default",
        }, {"Content-Type": "application/json"})
        self._token = out["access_token"]
        self._token_expires = time.time() + int(out.get("expires_in", 3600))
        return self._token

    def get_items(self, asins):
        """Return {asin: {title, price_amount, price_display, list_display,
        availability, merchant} | None} plus a list of error strings."""
        results, errors = {}, []
        for i in range(0, len(asins), BATCH_SIZE):
            batch = asins[i:i + BATCH_SIZE]
            if i:
                time.sleep(RATE_DELAY)
            payload = {
                "itemIds": batch,
                "itemIdType": "ASIN",
                "marketplace": MARKETPLACE,
                "partnerTag": PARTNER_TAG,
                "condition": "New",
                "resources": RESOURCES,
            }
            resp = self._call_with_retry(
                f"{API_BASE}/catalog/v1/getItems", payload,
                {"Authorization": f"Bearer {self.token()}",
                 "Content-Type": "application/json",
                 "x-marketplace": MARKETPLACE})
            for err in resp.get("errors", []):
                errors.append(f"{err.get('code')}: {err.get('message')}")
            for item in resp.get("itemsResult", {}).get("items", []):
                results[item.get("asin")] = self._parse_item(item)
        return results, errors

    def _call_with_retry(self, url, payload, headers, attempts=3):
        delay = 2.0
        for n in range(attempts):
            try:
                return self._http(url, payload, headers)
            except ApiUnavailable as e:
                if n == attempts - 1:
                    raise
                time.sleep(delay)
                delay *= 2

    def _parse_item(self, item):
        listings = (item.get("offersV2") or {}).get("listings") or []
        best = None
        for li in listings:
            if li.get("isBuyBoxWinner"):
                best = li
                break
        if best is None and listings:
            best = listings[0]
        if best is None:
            return None
        money = ((best.get("price") or {}).get("money") or {})
        saving = (((best.get("price") or {}).get("savingBasis") or {}).get("money") or {})
        title = ((item.get("itemInfo") or {}).get("title") or {}).get("displayValue")
        return {
            "title": title,
            "price_amount": money.get("amount"),
            "price_display": money.get("displayAmount"),
            "list_display": saving.get("displayAmount"),
            "availability": ((best.get("availability") or {}).get("message")),
            "merchant": ((best.get("merchantInfo") or {}).get("name")),
        }

    def search_items(self, keywords):
        """Resolve keywords -> candidate ASINs (top 5). Used by --resolve only."""
        payload = {
            "keywords": keywords,
            "marketplace": MARKETPLACE,
            "partnerTag": PARTNER_TAG,
            "searchIndex": "All",
            "itemCount": 5,
            "resources": ["itemInfo.title", "offersV2.listings.price",
                          "offersV2.listings.isBuyBoxWinner"],
        }
        resp = self._call_with_retry(
            f"{API_BASE}/catalog/v1/searchItems", payload,
            {"Authorization": f"Bearer {self.token()}",
             "Content-Type": "application/json",
             "x-marketplace": MARKETPLACE})
        cands = []
        for item in resp.get("searchResult", {}).get("items", []):
            parsed = self._parse_item(item)
            cands.append({"asin": item.get("asin"),
                          "title": parsed.get("title") if parsed else None,
                          "price_display": parsed.get("price_display") if parsed else None})
        return cands


class MockApi:
    """Test double: serves getItems responses from a JSON file."""

    def __init__(self, path):
        with open(path, encoding="utf-8") as fh:
            self.data = json.load(fh)

    def get_items(self, asins):
        api = CreatorsApi.__new__(CreatorsApi)  # reuse parser, no network
        results, errors = {}, []
        items = self.data.get("itemsResult", {}).get("items", [])
        by_asin = {it.get("asin"): it for it in items}
        for err in self.data.get("errors", []):
            errors.append(f"{err.get('code')}: {err.get('message')}")
        for asin in asins:
            item = by_asin.get(asin)
            if item is None:
                errors.append(f"ItemNotAccessible: mock has no data for {asin}")
                continue
            results[asin] = api._parse_item(item)
        return results, errors

    def search_items(self, keywords):  # pragma: no cover - not used in tests
        return []


# ------------------------------------------------------------- HTML rewriting

def rewrite_price_est(raw, block_id, current_text, new_display):
    """Replace the first $ amount in the .product-price-est div of one block.
    Returns (new_raw, reason) — reason None on success."""
    m = re.search(r'id="' + re.escape(block_id) + r'"', raw)
    if not m:
        return raw, f"block id {block_id} not found"
    div_re = re.compile(r'class="product-price-est"[^>]*>(.*?)</div>', re.S)
    dm = div_re.search(raw, m.start())
    if not dm:
        return raw, f"price-est div not found after block {block_id}"
    inner = dm.group(1)
    if norm_ws(strip_tags(inner)) != norm_ws(current_text):
        return raw, (f"stale map: price-est in block {block_id} now reads "
                     f"{norm_ws(strip_tags(inner))[:60]!r}, map says "
                     f"{norm_ws(current_text)[:60]!r}")
    new_inner = replace_first_amount(inner, new_display)
    if new_inner is None:
        return raw, f"no $ amount in price-est of block {block_id}"
    return raw[:dm.start(1)] + new_inner + raw[dm.end(1):], None


def rewrite_table_cell(raw, table_index, row_label, current_text, new_display):
    """Replace the first $ amount in the price cell of one table row.
    The cell is identified by its current text (must be unique in the file).
    Returns (new_raw, reason)."""
    # find the row whose label cell matches row_label
    row_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
    target_row = None
    for rm in row_re.finditer(raw):
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rm.group(1), re.S | re.I)
        texts = [norm_ws(strip_tags(c)) for c in cells]
        if any(norm_ws(row_label) == t or norm_ws(row_label) in t for t in texts):
            target_row = rm
            break
    if target_row is None:
        return raw, f"table row {row_label!r} not found"
    # within the row, find the cell whose text equals current_text
    row_html = target_row.group(1)
    cell_re = re.compile(r"(<t[hd][^>]*>)(.*?)(</t[hd]>)", re.S | re.I)
    matches = []
    for cm in cell_re.finditer(row_html):
        if norm_ws(strip_tags(cm.group(2))) == norm_ws(current_text):
            matches.append(cm)
    if not matches:
        return raw, (f"stale map: no cell reading {norm_ws(current_text)[:60]!r} "
                     f"in row {row_label!r}")
    if len(matches) > 1:
        return raw, f"ambiguous: {len(matches)} cells read {current_text!r} in row {row_label!r}"
    cm = matches[0]
    new_inner = replace_first_amount(cm.group(2), new_display)
    if new_inner is None:
        return raw, f"no $ amount in table cell for {row_label!r}"
    row_start = target_row.start(1)
    new_row = (row_html[:cm.start(2)] + new_inner + row_html[cm.end(2):])
    return raw[:row_start] + new_row + raw[target_row.end(1):], None


def stamp_page(raw, stamp_text):
    stamp = f"<!-- smartgearpick price-sync: prices checked {stamp_text} -->"
    # Remove any previous stamp(s) first, so a page keeps exactly one.
    raw = STAMP_RE.sub("", raw)
    idx = raw.rfind("</body>")
    if idx == -1:
        return raw + "\n" + stamp + "\n"
    return raw[:idx] + stamp + "\n" + raw[idx:]


# --------------------------------------------------------------------- modes

def run_sync(args):
    with open(args.map, encoding="utf-8") as fh:
        amap = json.load(fh)
    if args.mock:
        api = MockApi(args.mock)
    else:
        cid = os.environ.get("AMAZON_CLIENT_ID")
        csec = os.environ.get("AMAZON_CLIENT_SECRET")
        if not cid or not csec:
            print("ERROR: AMAZON_CLIENT_ID / AMAZON_CLIENT_SECRET are not set.",
                  file=sys.stderr)
            return 1
        api = CreatorsApi(cid, csec)

    products = [p for p in amap["products"]
                if p.get("asin") and p.get("asin_verified")]
    asins = [p["asin"] for p in products]
    if not asins:
        print("No verified ASINs in the map — nothing to sync.")
        return 0
    try:
        offers, errors = api.get_items(asins)
    except ApiUnavailable as e:
        print(f"ERROR: Amazon API unavailable ({e}) — no files changed.",
              file=sys.stderr)
        return 2

    stamp = utcnow()
    changed, skipped, changed_pages = [], [], set()
    not_auto_count = 0  # structured fields deliberately left manual
    map_changed = False
    for prod in products:
        asin = prod["asin"]
        offer = offers.get(asin)
        if offer is None:
            skipped.append({"asin": asin, "product": prod["product"],
                            "reason": "no offer returned (out of stock / not accessible?)"})
            continue
        if not offer.get("price_display"):
            skipped.append({"asin": asin, "product": prod["product"],
                            "reason": "offer has no price"})
            continue
        new_price = parse_amount(offer["price_display"])
        for field in prod["structured_fields"]:
            if not field.get("auto_updatable"):
                not_auto_count += 1  # range / tier label: left manual by design
                continue
            page_path = os.path.join(args.repo, field["page"])
            if not os.path.exists(page_path):
                skipped.append({"asin": asin, "product": prod["product"],
                                "reason": f"page missing: {field['page']}"})
                continue
            with open(page_path, encoding="utf-8") as fh:
                raw = fh.read()
            old_first = parse_amount(field["current"])
            if old_first is not None and new_price is not None and old_first == new_price:
                continue  # already current
            if field["kind"] == "price-est":
                new_raw, reason = rewrite_price_est(
                    raw, field["block_id"], field["current"], offer["price_display"])
            elif field["kind"] == "table-cell":
                new_raw, reason = rewrite_table_cell(
                    raw, field.get("table", 0), field["row_label"],
                    field["current"], offer["price_display"])
            else:
                reason = f"unknown field kind {field['kind']!r}"
                new_raw = raw
            if reason:
                skipped.append({"asin": asin, "product": prod["product"],
                                "field": field["kind"], "page": field["page"],
                                "reason": reason})
                continue
            # availability sanity note (qualifier text is left untouched)
            avail = offer.get("availability") or ""
            note = None
            if "out of stock" in field["current"].lower() and "in stock" in avail.lower():
                note = "field text says out of stock but API says in stock — qualifier left for human review"
            changed.append({"asin": asin, "product": prod["product"],
                            "page": field["page"], "kind": field["kind"],
                            "old": field["current"], "new_display": offer["price_display"],
                            "list_display": offer.get("list_display"),
                            "availability": avail,
                            "merchant": offer.get("merchant"), "note": note})
            changed_pages.add(field["page"])
            if not args.dry_run:
                new_raw = stamp_page(new_raw, f"{stamp} (Amazon Creators API)")
                with open(page_path, "w", encoding="utf-8") as fh:
                    fh.write(new_raw)
                # keep the map in sync so the next run's stale-check passes
                field["current"] = replace_first_amount(field["current"],
                                                        offer["price_display"])
                field["current_price"] = new_price
                map_changed = True

    if map_changed and not args.dry_run:
        with open(args.map, "w", encoding="utf-8") as fh:
            json.dump(amap, fh, indent=2, ensure_ascii=False)

    log = {"run_at_utc": stamp, "mode": "dry-run" if args.dry_run else "sync",
           "asins_checked": len(asins), "changed": changed,
           "skipped": skipped, "api_errors": errors,
           "fields_left_manual": not_auto_count,
           "pages_changed": sorted(changed_pages)}
    with open(args.log, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)
    print(f"checked {len(asins)} ASINs, {len(changed)} field(s) changed "
          f"on {len(changed_pages)} page(s), {len(skipped)} skipped, "
          f"{len(errors)} API error(s), {not_auto_count} field(s) left manual"
          + (" (dry run — nothing written)" if args.dry_run else ""))
    for c in changed:
        print(f"  CHANGED {c['product'][:50]:50s} {c['page']} "
              f"{c['old'][:40]!r} -> {c['new_display']}")
        if c.get("note"):
            print(f"    NOTE: {c['note']}")
    for s in skipped:
        print(f"  SKIPPED {s.get('product', s.get('asin'))}: {s['reason']}")
    for e in errors:
        print(f"  API ERROR: {e}")
    return 0


def run_resolve(args):
    with open(args.map, encoding="utf-8") as fh:
        amap = json.load(fh)
    cid = os.environ.get("AMAZON_CLIENT_ID")
    csec = os.environ.get("AMAZON_CLIENT_SECRET")
    if not cid or not csec:
        print("ERROR: AMAZON_CLIENT_ID / AMAZON_CLIENT_SECRET are not set.",
              file=sys.stderr)
        return 1
    api = CreatorsApi(cid, csec)
    todo = [p for p in amap["products"]
            if not p.get("asin") and p.get("has_amazon_link") and p.get("search_keywords")]
    out = []
    for prod in todo:
        try:
            cands = api.search_items(prod["search_keywords"])
        except ApiUnavailable as e:
            print(f"ERROR: API unavailable during resolve ({e})", file=sys.stderr)
            return 2
        time.sleep(RATE_DELAY)
        out.append({"product": prod["product"],
                    "search_keywords": prod["search_keywords"],
                    "pages": prod["pages"],
                    "candidates": cands,
                    "verified": False})
    with open(args.resolve_out, "w", encoding="utf-8") as fh:
        json.dump({"generated_at_utc": utcnow(), "candidates": out},
                  fh, indent=2, ensure_ascii=False)
    print(f"{len(out)} products resolved to candidates (NOT verified, NOT "
          f"written to the map) -> {args.resolve_out}")
    print("A human must check each candidate title against the product, then")
    print("set asin + asin_verified=true in asin-map.json.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="SmartGearPick Amazon price sync")
    ap.add_argument("--map", default="asin-map.json")
    ap.add_argument("--repo", default=".", help="repo root containing the HTML files")
    ap.add_argument("--log", default="price-sync-log.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", default=None, help="mock getItems JSON (test mode)")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--resolve-out", default="asin-resolution-candidates.json")
    args = ap.parse_args()
    if args.resolve:
        return run_resolve(args)
    return run_sync(args)


if __name__ == "__main__":
    sys.exit(main())
