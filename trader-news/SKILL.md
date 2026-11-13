---
name: trader-news
description: >-
  News Monitor for gold and silver. Pulls the latest gold and silver price
  headlines (Google News), shows how far each metal has moved from the
  previous settlement, and tags what usually moves them: the Fed, US
  inflation and jobs data, the dollar and yields, geopolitics, central-bank
  buying, ETF flows, physical demand, supply. Shows only what is new since
  the last check. Use when the user says "any news on gold", "why is silver
  moving", "what's driving gold today", "check the news", or after
  /trader-scanner and before /trader-entry.
argument-hint: "[GOLD | SILVER]"
---

> **Gold and silver edition.** Prices are COMEX futures from Yahoo (GC=F for gold, SI=F for silver), in US dollars per ounce. Type GOLD, SILVER, XAUUSD or XAGUSD; the scripts translate. All times are Dubai (UTC+4). The day-trading session is 12:00 to 23:30 Dubai (London open to late New York). Your broker's spot or CFD price can differ from the futures by a few dollars.

# trader-news

A clean chart can still be about to move hard on a CPI print or a Fed
speaker. This skill reads the headlines for each metal you watch and tells
you only what is new, with today's move next to it.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py"                          # watchlist + plan + portfolio
python3 "${CLAUDE_SKILL_DIR}/news.py" --tickers GOLD SILVER --hours 12
python3 "${CLAUDE_SKILL_DIR}/news.py" --tickers GOLD --all --hours 72
python3 "${CLAUDE_SKILL_DIR}/news.py" --json
```

Other flags: `--no-moves`, `--move-pct` (1.0), `--dry-run` (do not mark items
seen), `--offline DIR`.

## Sources

| source | what |
| --- | --- |
| Yahoo chart (GC=F, SI=F) | last price vs the previous settlement; MOVING when 1 % or more |
| Google News RSS (global English) | `("gold price" OR "spot gold" OR "gold futures" OR XAUUSD) when:2d`, and the same for silver |
| `trader/state/news.json` | what was already shown (30 days), so each story shows once |

Not fetched: the economic calendar. Before trading, check today's US releases
(CPI, PCE, payrolls, jobless claims, FOMC) on forexfactory.com or
investing.com/economic-calendar, and say if one lands inside the trade.

## Reading it

- Tags: fed, inflation, jobs, dollar, geopolitics, central banks, flows,
  demand, supply, levels, crash. A tag means the words appear, not that the
  story matters.
- A story tagged for both metals (GOLD,SILVER) mentions both.
- Headlines are leads, not facts: open the story before acting on it.
- Never say what the metal will do next.

## Steps

1. Run `news.py` (or `--tickers GOLD`). Say today's move and the two or
   three newest stories that matter, in one line each.
2. Name any scheduled US release or Fed event inside today's session.
3. If something big is pending (a Fed decision, CPI in an hour), say the
   setup may not survive it, then hand off to `/trader-entry`.

## Safety

- Education and tooling, not financial advice.
- Nothing in this pack places an order. The user places it themselves in their own broker's app
  (MT4/MT5, cTrader, a futures platform...), and only after trader-risk passed that exact order today.
