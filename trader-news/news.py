#!/usr/bin/env python3
"""News monitor for trader-news (gold and silver edition). Standard library only.

Watches gold and silver headlines and prints only what is new since the last
check, newest first, with how far each metal has moved today and tags for
what usually moves it (the Fed, US inflation and jobs data, the dollar and
yields, geopolitics, central-bank buying, ETF flows, physical demand).

    python3 news.py                                  # watchlist + plan + portfolio symbols
    python3 news.py --tickers GOLD SILVER
    python3 news.py --tickers GOLD --all --hours 72  # everything in the last 3 days, seen or not
    python3 news.py --no-moves                       # skip the price line per symbol

Your symbols, when --tickers is not given: every hit in trader/watchlist.json
(trader-scanner), the symbol in trader/plan.json (trader-exit) and the
positions in trader/portfolio.json. GOLD/XAUUSD and SILVER/XAGUSD all work.

Sources, per symbol:
  - The move: Yahoo Finance's chart for the COMEX front-month future
    (GC=F for gold, SI=F for silver; unofficial, can lag), last price
    against the previous settlement:
    https://query2.finance.yahoo.com/v8/finance/chart/GC=F?range=1d&interval=5m
  - Headlines: Google News RSS (global English edition), searched by topic:
    https://news.google.com/rss/search?q=("gold price" OR XAUUSD ...)+when:2d
  Scheduled data (FOMC, CPI, PCE, payrolls) is not fetched: check an economic
  calendar (forexfactory.com, investing.com/economic-calendar) every morning.

Times print in Dubai time. State: trader/state/news.json remembers what you
have seen (30 days), so an item shows once. Offline: --offline DIR reads
google-<TICKER>.xml and chart-<TICKER>.json from DIR.

Headlines are leads, not facts: open the story before acting, and treat
nothing here as advice.
"""

import argparse
import datetime as _dt
import email.utils
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET  # noqa: N817

GNEWS = "https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en"
CHART = "https://%s.finance.yahoo.com/v8/finance/chart/%s?range=1d&interval=5m"
Dubai = _dt.timedelta(hours=4)
BROWSER_UA = "Mozilla/5.0 (compatible; day-trader-skill-metals/1.0; +https://github.com/Jakeschincariol/day-trader-skill)"
KEEP_DAYS = 30
MOVE_PCT = 1.0  # a metal this far from the previous settlement is flagged as moving

KEYWORDS = [
    ("fed", r"\bFed\b|\bFOMC\b|\bPowell\b|rate (?:cut|hike|decision)s?|\binterest rates?\b|\bdovish\b|\bhawkish\b"),
    ("inflation", r"\bCPI\b|\bPCE\b|\bPPI\b|\binflation\b"),
    ("jobs", r"\bpayrolls?\b|\bNFP\b|\bjobs report\b|\bunemployment\b|\bjobless claims\b"),
    ("dollar", r"\bdollar\b|\bDXY\b|\btreasury yields?\b|\byields?\b|\bbond market\b"),
    ("geopolitics", r"\bwar\b|\bsanctions?\b|\bmissile\b|\bstrikes?\b|\bceasefire\b|\btariffs?\b|\bsafe[- ]haven\b|\bconflict\b"),
    ("central banks", r"\bcentral banks?\b|\bPBOC\b|\bRBI\b|\breserves?\b"),
    ("flows", r"\bETFs?\b|\bGLD\b|\bSLV\b|\binflows?\b|\boutflows?\b|\bCOT\b|\bpositioning\b"),
    ("demand", r"\bjewel+ery\b|\bphysical demand\b|\bimports?\b|\bsolar\b|\bindustrial demand\b|\bDhanteras\b|\bwedding season\b"),
    ("supply", r"\bmines?\b|\bmining\b|\boutput\b|\bdeficit\b|\bsupply\b"),
    ("levels", r"\brecord high\b|\ball-time high\b|\bresistance\b|\bsupport\b|\b\$\d{1,2},?\d{3}\b"),
    ("crash", r"\bplunges?\b|\bslumps?\b|\btumbles?\b|\bsurges?\b|\bsoars?\b|\bspikes?\b"),
]


class NewsError(Exception):
    pass


# ---------------------------------------------------------------- time

def to_ist(utc):
    """Aware or naive UTC -> naive Dubai (UTC+4, no daylight saving) wall-clock time."""
    if utc.tzinfo is not None:
        utc = utc.astimezone(_dt.timezone.utc)
    return utc.replace(tzinfo=None) + Dubai


# ---------------------------------------------------------------- inputs

def load_json(path):
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def watch_from_files(portfolio="trader/portfolio.json", watchlist="trader/watchlist.json",
                     plan="trader/plan.json"):
    """{ticker: name or None}: the scanner's hits, the planned trade and your holdings."""
    out = {}
    wl = load_json(watchlist) or {}
    for h in wl.get("hits", []):
        sym = h.get("symbol") or h.get("ticker")
        if sym:
            out[sym.upper()] = h.get("name")
    pl = load_json(plan) or {}
    if pl.get("symbol"):
        out.setdefault(pl["symbol"].upper(), pl.get("name"))
    pf = load_json(portfolio) or {}
    for p in pf.get("positions", []):
        sym = p.get("ticker") or p.get("symbol")
        if sym:
            out[sym.upper()] = p.get("name") or out.get(sym.upper())
    return out


# ---------------------------------------------------------------- fetching

class Fetcher(object):
    def __init__(self, offline=None, pause=0.15):
        self.offline = offline
        self.pause = pause
        self._last = 0.0

    def get(self, url, name):
        if self.offline:
            path = os.path.join(self.offline, name)
            if not os.path.isfile(path):
                raise NewsError("offline: no file %s" % path)
            with open(path, "rb") as fh:
                return fh.read()
        gap = time.time() - self._last
        if gap < self.pause:
            time.sleep(self.pause - gap)
        self._last = time.time()
        headers = {"User-Agent": BROWSER_UA, "Accept-Encoding": "gzip"}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return data
        except urllib.error.HTTPError as exc:
            raise NewsError("HTTP %s for %s" % (exc.code, url))
        except urllib.error.URLError as exc:
            raise NewsError("could not reach %s: %s" % (url, exc.reason))


METALS = {  # what you type -> Yahoo's COMEX futures chart
    "GOLD": "GC=F", "XAU": "GC=F", "XAUUSD": "GC=F", "GC": "GC=F", "MGC": "MGC=F",
    "SILVER": "SI=F", "XAG": "SI=F", "XAGUSD": "SI=F", "SI": "SI=F", "SIL": "SIL=F",
}
TOPIC = {  # Google News search and the mention pattern, per metal
    "GC=F": ('("gold price" OR "gold prices" OR "spot gold" OR "gold futures" OR XAUUSD)', r"\bgold\b|\bXAU"),
    "MGC=F": ('("gold price" OR "gold prices" OR "spot gold" OR "gold futures" OR XAUUSD)', r"\bgold\b|\bXAU"),
    "SI=F": ('("silver price" OR "silver prices" OR "spot silver" OR "silver futures" OR XAGUSD)', r"\bsilver\b|\bXAG"),
    "SIL=F": ('("silver price" OR "silver prices" OR "spot silver" OR "silver futures" OR XAGUSD)', r"\bsilver\b|\bXAG"),
}


def yahoo_symbol(ticker):
    """GOLD/XAUUSD -> GC=F, SILVER/XAGUSD -> SI=F (URL-safe). Anything else passes through."""
    t = ticker.strip().upper()
    return urllib.parse.quote(METALS.get(t, t), safe=".^-=")


def short_name(name):
    """"Tata Elxsi Limited" -> "Tata Elxsi": what news stories call the company."""
    n = re.sub(r"\s+", " ", str(name or "")).strip()
    n = re.sub(r"\s*\b(Limited|Ltd\.?|LIMITED|LTD\.?)$", "", n).strip()
    if n.isupper():
        n = n.title()
    return n


def news_query(ticker, name, hours):
    days = max(1, int(-(-hours // 24)))
    topic = TOPIC.get(METALS.get(ticker.strip().upper(), ticker.strip().upper()))
    if topic:
        return urllib.parse.quote_plus("%s when:%dd" % (topic[0], days))
    who = '"%s"' % short_name(name) if short_name(name) else '"%s"' % ticker
    return urllib.parse.quote_plus("%s when:%dd" % (who, days))


# ---------------------------------------------------------------- parsing

def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _text(el, name):
    for c in el.iter():
        if _local(c.tag) == name:
            return (c.text or "").strip()
    return ""


def parse_time(value):
    """RFC 822 (RSS) or ISO 8601 (Atom) -> aware UTC datetime, or None."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        d = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        d = None
    if d is None:
        try:
            d = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return d.astimezone(_dt.timezone.utc)


def parse_rss(data, ticker):
    """Yahoo headline RSS -> items."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise NewsError("RSS for %s is not valid XML: %s" % (ticker, exc))
    out = []
    for it in root.iter("item"):
        title = _text(it, "title")
        link = _text(it, "link")
        guid = _text(it, "guid") or link
        src = _text(it, "source") or "Google News"
        if src and title.endswith(" - " + src):
            title = title[: -len(" - " + src)]
        out.append({"id": "rss:" + guid, "source": src[:13], "kind": "headline",
                    "ticker": ticker, "title": title, "summary": _text(it, "description"),
                    "link": link, "time": parse_time(_text(it, "pubDate"))})
    return out


def parse_chart(data, ticker):
    """Yahoo chart JSON -> {"ticker", "price", "prev_close", "pct", "time"} or raise."""
    try:
        doc = json.loads(data.decode("utf-8") if isinstance(data, bytes) else data)
        meta = doc["chart"]["result"][0]["meta"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise NewsError("chart for %s is not usable" % ticker)
    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    if not price or not prev:
        raise NewsError("chart for %s has no price" % ticker)
    when = meta.get("regularMarketTime")
    return {"ticker": ticker, "name": short_name(meta.get("longName") or meta.get("shortName")),
            "price": round(float(price), 2), "prev_close": round(float(prev), 2),
            "pct": round((float(price) / float(prev) - 1) * 100, 2),
            "time": _dt.datetime.fromtimestamp(when, _dt.timezone.utc) if when else None}


def collect_moves(fetcher, watch, errors=None):
    errors = [] if errors is None else errors
    out = []
    for t in sorted(watch):
        name = "chart-%s.json" % t
        try:
            try:
                data = fetcher.get(CHART % ("query2", yahoo_symbol(t)), name)
            except NewsError as exc:
                if fetcher.offline or not re.search(r"HTTP (429|5\d\d)", str(exc)):
                    raise
                data = fetcher.get(CHART % ("query1", yahoo_symbol(t)), name)
            out.append(parse_chart(data, t))
        except NewsError as exc:
            if not (fetcher.offline and "no file" in str(exc)):
                errors.append("price for %s: %s" % (t, exc))
    return out


def mention_patterns(watch):
    pats = {}
    for t, name in watch.items():
        alts = [r"\(%s\)" % re.escape(t), r"\b%s\b" % re.escape(t)]
        topic = TOPIC.get(METALS.get(t, t))
        if topic:
            alts.append(topic[1])
        elif name and len(name) >= 4:
            alts.append(r"\b%s\b" % re.escape(name).replace(r"\ ", r"[\s-]"))
        pats[t] = re.compile("|".join(alts), re.I)
    return pats


def tag(items, watch):
    """Which of your tickers each item touches, and why it matters."""
    pats = mention_patterns(watch)
    for it in items:
        hay = "%s %s" % (it["title"], it.get("summary") or "")
        touches = {it["ticker"]} if it["ticker"] in watch else set()
        for t, rx in pats.items():
            if rx.search(hay):
                touches.add(t)
        it["touches"] = sorted(touches)
        it["tags"] = [label for label, rx in KEYWORDS if re.search(rx, hay, re.I)]
    return items


def dedupe(items):
    """One item per story: same id, or same link, or same title the same day."""
    seen, out = {}, []
    for it in items:
        keys = [it["id"], it["link"],
                "%s|%s" % (re.sub(r"\W+", " ", it["title"].lower()).strip(),
                           it["time"].date() if it["time"] else "")]
        hit = next((seen[k] for k in keys if k and k in seen), None)
        if hit is not None:
            for t in it.get("touches", []):
                if t not in hit["touches"]:
                    hit["touches"].append(t)
            hit["touches"].sort()
            continue
        for k in keys:
            if k:
                seen[k] = it
        out.append(it)
    return out


def fingerprint(it):
    return hashlib.sha1(it["id"].encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- the check

def collect(fetcher, watch, hours=48, errors=None):
    """Headlines for each ticker, searched by the company name in watch (or the ticker)."""
    errors = [] if errors is None else errors
    items = []
    for t in sorted(watch):
        try:
            items += parse_rss(fetcher.get(GNEWS % news_query(t, watch[t], hours), "google-%s.xml" % t), t)
        except NewsError as exc:
            errors.append("headlines for %s: %s" % (t, exc))
    return items


def select(items, state, now, hours=48, show_all=False):
    """Items within the window; only unseen ones unless show_all."""
    seen = state.setdefault("seen", {})
    cutoff = now - _dt.timedelta(hours=hours)
    ahead = now + _dt.timedelta(minutes=10)  # a pinned --now: nothing from after it
    out = []
    for it in items:
        if it["time"] is not None and (it["time"] < cutoff or it["time"] > ahead):
            continue
        fp = fingerprint(it)
        it["new"] = fp not in seen
        if it["new"] or show_all:
            out.append(it)
    out.sort(key=lambda i: (i["time"] or now), reverse=True)
    return out


def remember(items, state, now):
    seen = state.setdefault("seen", {})
    stamp = now.isoformat()
    for it in items:
        seen.setdefault(fingerprint(it), stamp)
    cutoff = (now - _dt.timedelta(days=KEEP_DAYS)).isoformat()
    state["seen"] = {k: v for k, v in seen.items() if v >= cutoff}
    state["last_check"] = stamp


def render_moves(moves, move_pct=MOVE_PCT):
    out = []
    for m in moves:
        flag = "MOVING" if abs(m["pct"]) >= move_pct else ""
        when = (" at %s Dubai" % to_ist(m["time"]).strftime("%H:%M")) if m.get("time") else ""
        out.append("%-10s $%s %+.2f%% vs yesterday's close $%s%s  %s" % (
            m["ticker"], "{:,.2f}".format(m["price"]), m["pct"], "{:,.2f}".format(m["prev_close"]),
            when, flag))
    return out


def render(items, errors, now, moves=None, move_pct=MOVE_PCT):
    out = render_moves(moves or [], move_pct)
    if out:
        out.append("")
    if not items:
        out.append("Nothing new.")
    for it in items:
        when = to_ist(it["time"]).strftime("%Y-%m-%d %H:%M Dubai") if it["time"] else "time unknown"
        mark = "!" if it.get("important") else " "
        who = ",".join(it["touches"]) or it["ticker"]
        out.append("%s %s  %-11s %-13s %s" % (mark, when, who, it["source"], it["title"]))
        extra = []
        if it["tags"]:
            extra.append("tags: " + ", ".join(it["tags"]))
        extra.append(it["link"])
        out.append("      " + "  ".join(extra))
    for e in errors:
        out.append("note: %s" % e)
    out.append("Checked %s. Headlines are leads, not facts; open the story before acting. "
               "Check the economic calendar (Fed, CPI, payrolls) too. Not financial advice."
               % to_ist(now).strftime("%Y-%m-%d %H:%M Dubai"))
    return "\n".join(out) + "\n"


def _json_ready(items):
    out = []
    for it in items:
        d = dict(it)
        d["time"] = it["time"].isoformat() if it["time"] else None
        out.append(d)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tickers", nargs="*", help="default: watchlist + plan + portfolio")
    ap.add_argument("--portfolio", default="trader/portfolio.json")
    ap.add_argument("--watchlist", default="trader/watchlist.json")
    ap.add_argument("--plan", default="trader/plan.json")
    ap.add_argument("--state", default="trader/state/news.json")
    ap.add_argument("--hours", type=float, default=48, help="ignore items older than this")
    ap.add_argument("--all", action="store_true", help="show seen items too")
    ap.add_argument("--no-moves", action="store_true", help="skip the price line per ticker")
    ap.add_argument("--move-pct", type=float, default=MOVE_PCT, help="flag a move this big (percent)")
    ap.add_argument("--offline", metavar="DIR")
    ap.add_argument("--now", help="ISO time, for reproducible runs")
    ap.add_argument("--dry-run", action="store_true", help="do not update the state file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.tickers:
        watch = {t.upper(): None for t in args.tickers}
        known = watch_from_files(args.portfolio, args.watchlist, args.plan)
        watch.update({t: known[t] for t in watch if known.get(t)})
    else:
        watch = watch_from_files(args.portfolio, args.watchlist, args.plan)
    if not watch:
        print("news: no tickers. Pass --tickers, or run /trader-scanner first (it writes "
              "trader/watchlist.json).", file=sys.stderr)
        return 2
    now = parse_time(args.now) if args.now else _dt.datetime.now(_dt.timezone.utc)
    state = load_json(args.state) or {}
    errors = []
    fetcher = Fetcher(offline=args.offline)
    moves = collect_moves(fetcher, watch, errors)  # also gives each company's name for the news search
    for m in moves:
        if m.get("name") and not watch.get(m["ticker"]):
            watch[m["ticker"]] = m["name"]
    if args.no_moves:
        moves = []
    items = collect(fetcher, watch, args.hours, errors=errors)
    items = dedupe(tag(items, watch))
    shown = select(items, state, now, hours=args.hours, show_all=args.all)
    if args.json:
        mv = [dict(m, time=m["time"].isoformat() if m.get("time") else None,
                   moving=abs(m["pct"]) >= args.move_pct) for m in moves]
        print(json.dumps({"checked": now.isoformat(), "moves": mv, "items": _json_ready(shown),
                          "notes": errors}, indent=2))
    else:
        sys.stdout.write(render(shown, errors, now, moves, args.move_pct))
    if not args.dry_run:
        remember(items, state, now)
        folder = os.path.dirname(args.state)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(args.state, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
            fh.write("\n")
    return 0 if any(i["new"] for i in shown) else 1


if __name__ == "__main__":
    sys.exit(main())
