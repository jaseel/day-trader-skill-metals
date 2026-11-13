#!/usr/bin/env python3
"""Synthetic GC=F / SI=F Yahoo v8 charts for offline tests (NOT real prices)."""
import datetime as dt, json, math, os, random, sys

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
HOL = {"2026-09-07", "2026-11-26"}  # early-close days still have bars; full closures none in range
END = dt.datetime(2026, 11, 13, 9, 15)  # 13:15 Dubai, last bar starts 09:10 UTC


def series(seed, start_px, sig5, vol0, interval_min, days_back, daily=False):
    rnd = random.Random(seed)
    ts, o, h, l, c, v = [], [], [], [], [], []
    px = start_px
    d = END.date() - dt.timedelta(days=days_back)
    while d <= END.date():
        if d.weekday() < 5 and d.isoformat() not in ("2026-01-01", "2026-04-03", "2026-12-25"):
            if daily:
                op = px
                cl = op * math.exp(rnd.gauss(0.0004, 0.012))
                hi, lo = max(op, cl) * (1 + abs(rnd.gauss(0, 0.004))), min(op, cl) * (1 - abs(rnd.gauss(0, 0.004)))
                t = dt.datetime.combine(d, dt.time(4, 0))
                if t <= END:
                    ts.append(int((t - dt.datetime(1970, 1, 1)).total_seconds()))
                    o.append(round(op, 2)); h.append(round(hi, 2)); l.append(round(lo, 2)); c.append(round(cl, 2))
                    v.append(int(vol0 * rnd.uniform(0.6, 1.4)))
                px = cl
            else:
                t = dt.datetime.combine(d, dt.time(0, 0))
                stop = dt.datetime.combine(d, dt.time(21, 0))
                while t < stop and t < END:
                    hour = t.hour
                    act = 1.6 if 12 <= hour < 16 else (1.2 if 7 <= hour < 12 else 0.7)
                    op = px
                    cl = op * math.exp(rnd.gauss(0, sig5 * act))
                    hi = max(op, cl) * (1 + abs(rnd.gauss(0, sig5 * 0.5)))
                    lo = min(op, cl) * (1 - abs(rnd.gauss(0, sig5 * 0.5)))
                    ts.append(int((t - dt.datetime(1970, 1, 1)).total_seconds()))
                    o.append(round(op, 2)); h.append(round(hi, 2)); l.append(round(lo, 2)); c.append(round(cl, 2))
                    v.append(int(vol0 * act * rnd.uniform(0.5, 1.5)))
                    px = cl
                    t += dt.timedelta(minutes=interval_min)
        d += dt.timedelta(days=1)
    return ts, o, h, l, c, v


def plant_breakout(ts, o, h, l, c, v):
    """13 Nov: opening range 08:00-08:15 UTC (12:00-12:15 Dubai), then the 08:25 bar closes above it."""
    idx = {t: i for i, t in enumerate(ts)}
    base = int((dt.datetime(2026, 11, 13, 8, 0) - dt.datetime(1970, 1, 1)).total_seconds())
    i0 = idx[base]
    p = c[i0 - 1]
    path = [(p, p + 4, p - 3, p + 2), (p + 2, p + 6, p, p + 1), (p + 1, p + 3, p - 2, p + 3),  # range bars
            (p + 3, p + 5, p + 1, p + 4), (p + 4, p + 8, p + 3, p + 7.5),  # 08:15 inside, 08:20 closes above
            (p + 7.5, p + 9, p + 6, p + 8), ]
    for k, (op, hi, lo, cl) in enumerate(path):
        j = i0 + k
        o[j], h[j], l[j], c[j] = round(op, 2), round(hi, 2), round(lo, 2), round(cl, 2)
        v[j] = int(v[j] * (2.0 if k < 3 else 1.6))
    j = i0 + len(path)
    while j < len(ts):  # keep the rest continuous from the planted path
        shift = c[j - 1] - o[j]
        o[j] += shift; h[j] += shift; l[j] += shift; c[j] += shift
        o[j], h[j], l[j], c[j] = (round(x, 2) for x in (o[j], h[j], l[j], c[j]))
        j += 1


def doc(sym, name, ts, o, h, l, c, v, interval, rng):
    prev = c[-1]
    for i in range(len(ts) - 1, -1, -1):
        if (dt.datetime(1970, 1, 1) + dt.timedelta(seconds=ts[i])).date() < END.date() and interval != "1d":
            prev = c[i]; break
    if interval == "1d":
        prev = c[-2]
    meta = {"currency": "USD", "symbol": sym, "exchangeName": "CMX", "fullExchangeName": "COMEX",
            "instrumentType": "FUTURE", "regularMarketTime": ts[-1] + 300, "gmtoffset": -18000,
            "timezone": "EST", "exchangeTimezoneName": "America/New_York", "regularMarketPrice": c[-1],
            "chartPreviousClose": prev, "previousClose": prev, "longName": name, "shortName": name,
            "regularMarketVolume": sum(v[-100:]), "dataGranularity": interval, "range": rng, "priceHint": 2}
    return {"chart": {"result": [{"meta": meta, "timestamp": ts, "indicators": {"quote": [
        {"open": o, "high": h, "low": l, "close": c, "volume": v}]}}], "error": None}}


def dump(d, *names):
    for n in names:
        p = os.path.join(OUT, n)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            json.dump(d, fh)


g = series(1, 4020.0, 0.0008, 900, 5, 90)
plant_breakout(*g)
s = series(2, 50.4, 0.0013, 400, 5, 90)
gd = series(3, 3300.0, 0, 180000, 0, 200, daily=True)
sd = series(4, 38.0, 0, 60000, 0, 200, daily=True)
G = doc("GC=F", "Gold Dec 26", *g, "5m", "60d")
S = doc("SI=F", "Silver Dec 26", *s, "5m", "60d")
dump(G, "5m/GC=F.json", "5m/GOLD.json", "5m/GOLD-60d5m.json", "news/chart-GOLD.json", "alerts/yahoo-GOLD.json", "alerts/yahoo-GC=F.json")
dump(S, "5m/SI=F.json", "5m/SILVER.json", "5m/SILVER-60d5m.json", "news/chart-SILVER.json", "alerts/yahoo-SILVER.json", "alerts/yahoo-SI=F.json")
dump(doc("GC=F", "Gold Dec 26", *gd, "1d", "6mo"), "1d/GOLD.json")
dump(doc("SI=F", "Silver Dec 26", *sd, "1d", "6mo"), "1d/SILVER.json")
rss = """<?xml version="1.0"?><rss><channel>
<item><title>Gold steadies near $4,050 as traders await Fed speakers - Reuters</title><link>https://example.com/a</link><guid>a1</guid><pubDate>Fri, 13 Nov 2026 07:10:00 GMT</pubDate><source>Reuters</source></item>
<item><title>Spot gold edges up as dollar softens after US CPI - Kitco</title><link>https://example.com/b</link><guid>b1</guid><pubDate>Thu, 12 Nov 2026 14:00:00 GMT</pubDate><source>Kitco</source></item>
</channel></rss>"""
rss2 = """<?xml version="1.0"?><rss><channel>
<item><title>Silver jumps on solar demand outlook, gold firm - Bloomberg</title><link>https://example.com/c</link><guid>c1</guid><pubDate>Fri, 13 Nov 2026 06:30:00 GMT</pubDate><source>Bloomberg</source></item>
</channel></rss>"""
for n, x in (("news/google-GOLD.xml", rss), ("news/google-SILVER.xml", rss2)):
    with open(os.path.join(OUT, n), "w") as fh:
        fh.write(x)
print("ok", len(g[0]), "gold 5m bars;", len(gd[0]), "daily")
