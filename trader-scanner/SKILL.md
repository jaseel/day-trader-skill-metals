---
name: trader-scanner
description: >-
  Chart Scanner for gold and silver. Checks GOLD (XAUUSD) and SILVER (XAGUSD)
  for day-trading setups: before the session, daily-close setups (20-day
  closing-high breakouts, bull flags, a reclaim of the 20-day average,
  oversold RSI and oversold bounces); during the session, opening-range
  breakouts on 5-minute bars (range 12:00-12:15 Dubai). Writes
  trader/watchlist.json for the rest of the pack. Use when the user says
  "scan gold", "any setups on silver", "did gold break the opening range",
  "pre-market scan", "build my watchlist", "what's setting up", or at the
  start of a trading day.
argument-hint: "[universe | daily | orb] [--at HH:MM]"
---

> **Gold and silver edition.** Prices are COMEX futures from Yahoo (GC=F for gold, SI=F for silver), in US dollars per ounce. Type GOLD, SILVER, XAUUSD or XAGUSD; the scripts translate. All times are Dubai (UTC+4). The day-trading session is 12:00 to 23:30 Dubai (London open to late New York). Your broker's spot or CFD price can differ from the futures by a few dollars.

# trader-scanner

The scanner answers one question: is either metal setting up today? A scan
is a list of charts that match a rule, not a list of things to buy.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/scan.py" universe                       # GOLD + SILVER -> trader/universe.txt
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily                          # before 12:00 Dubai -> trader/watchlist.json
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily --symbols GOLD           # one metal
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb                            # after 12:20 Dubai -> trader/watchlist.json
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --at 12:45                 # cut the clock at 12:45 Dubai
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --json
```

Other flags: `--min-price` (5), `--min-volume` (0: futures volume is not
comparable to stock volume), `--or-minutes` (15), `--now "2026-11-13 12:35"`
(Dubai) to replay a moment, `--offline PATH` for saved Yahoo chart files.

## What it reads and writes

| file | what |
| --- | --- |
| `metals.txt` (this folder) | the default universe: GOLD and SILVER. Add MGC or SIL (micro futures) if you like |
| `trader/universe.txt` | written by `universe`; used instead of `metals.txt` when present |
| `trader/config.json` | `no_entries_after` (22:00) ends the orb scan's window |
| `trader/watchlist.json` | the hits: symbol, setup, price, level, time. trader-news, trader-entry and trader-exit read it |

## The setups

**daily** (closes only, today's unfinished bar dropped):
breakout_20d (last close above every close of the 20 before it), bull_flag
(up 10 %+ over 10 sessions, then 5 closes inside a 5 % range), reclaim_ma20,
oversold (RSI 14 under 30), oversold_bounce (RSI was under 30, today closed up).
On metals, 10 % flags are rare: most days the daily scan finds nothing, and
that is a normal answer.

**orb**: the opening range is the 12:00, 12:05 and 12:10 five-minute bars
(12:00-12:15 Dubai, the first quarter hour after the London open in winter).
A hit is the first completed bar after the range that CLOSES above the range
high. Run it after 12:20 Dubai.

## Steps

1. Before 12:00 Dubai: `scan.py daily`. Say what matched in one line each,
   or that nothing did.
2. After 12:20 Dubai: `scan.py orb`. Say which metal broke out, at what time
   and how far over the range high.
3. Hand off: `/trader-news GOLD`, then `/trader-entry GOLD`.

## Rules

- Every number comes from the tool. Free Yahoo data is unofficial and can lag.
- A hit is not a reason to trade. Check news and the economic calendar
  (US CPI, payrolls and Fed days move gold hard, usually at 16:30-17:30 or
  22:00-23:00 Dubai).
- COMEX holidays (Good Friday, Christmas, New Year) are closed; US holidays
  are treated as a 21:00 Dubai early close. Verify on cmegroup.com.

## Safety

- Education and tooling, not financial advice. A scan hit is not a recommendation.
- Nothing in this pack places an order. The user places it themselves in their own broker's app
  (MT4/MT5, cTrader, a futures platform...), and only after trader-risk passed that exact order today.
- Gold and silver CFDs and futures are leveraged: losses can exceed what you planned if a stop gaps.
