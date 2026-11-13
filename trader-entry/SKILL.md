---
name: trader-entry
description: >-
  Entry Timer for gold and silver. Watches a setup bar by bar and tells you
  the moment to get in. Reads free Yahoo 1-minute or 5-minute bars of COMEX
  gold (GC=F) or silver (SI=F), builds the opening range (12:00-12:15 Dubai
  by default) and calls the entry on the first completed bar that CLOSES
  above the range high, or above a level you give it, with an optional
  volume check. Says waiting and how far, triggered with the time and the
  price, expired, or not open yet, and writes trader/entry.json for
  /trader-exit. Long side only. It never places an order. Use when the user
  says "tell me when to get in", "watch gold", "has silver broken out", "did
  gold break the opening range", "entry signal", "time my entry", or after
  /trader-scanner and /trader-news, before /trader-exit.
argument-hint: "[GOLD | SILVER] [--setup orb|level] [--interval 5m|1m]"
---

> **Gold and silver edition.** Prices are COMEX futures from Yahoo (GC=F for gold, SI=F for silver), in US dollars per ounce. Type GOLD, SILVER, XAUUSD or XAGUSD; the scripts translate. All times are Dubai (UTC+4). The day-trading session is 12:00 to 23:30 Dubai (London open to late New York). Your broker's spot or CFD price can differ from the futures by a few dollars.

# trader-entry

The Entry Timer turns a setup into one moment: the bar that confirms it. A
price that pokes above the high in the middle of a bar is not an entry. A
bar that CLOSES above it is. Then it says the time and the price, writes them
down for the Exit Planner, and stops. Day trading loses most people money,
and a clean signal does not change that.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/entry.py" check GOLD                  # 15-minute opening range, 5-minute bars
python3 "${CLAUDE_SKILL_DIR}/entry.py" check GOLD --write          # also save trader/entry.json
python3 "${CLAUDE_SKILL_DIR}/entry.py" check GOLD --setup level --level 4100
python3 "${CLAUDE_SKILL_DIR}/entry.py" check SILVER --interval 1m --min-volume-x 1.5
python3 "${CLAUDE_SKILL_DIR}/entry.py" watch GOLD --until 22:00    # one line per closed bar, stops on the trigger
python3 "${CLAUDE_SKILL_DIR}/entry.py" watchlist                   # every hit in trader/watchlist.json
```

Other flags: `--or-minutes N` (default 15), `--json`, `--offline FILE`,
`--now "2026-11-13 12:35"` (Dubai) to replay a moment. `watch` with `--now`
or `--offline` replays the day bar by bar without waiting.

## The rule

- **Opening range (orb).** The high and low of the 12:00, 12:05 and 12:10
  five-minute bars (12:00-12:15 Dubai). The level to beat is the range high.
- **Level.** A price you give, like a 20-day high from `/trader-scanner` or
  a round number (4,100).
- **The trigger** is the first completed bar after the range that CLOSES
  above the level. A wick above is not a trigger.
- **The time** is that bar's close time (the 12:25 bar closes at 12:30).
- **Only closed bars count.** Yahoo's live tick is never a bar.
- **Time limits.** No entries before 12:30 or after 22:00 Dubai (config
  `no_entries_before` / `no_entries_after`). The session ends at 23:30.
- **What it says.** Waiting (and how far), triggered, expired, or no data.
  Before 12:00: not open yet. Before 12:15: the range is still forming.
  Weekends and COMEX holidays: closed.

## Steps

1. Get the metal from the user, or run `entry.py watchlist` after
   `/trader-scanner`. Check `/trader-news` first.
2. Run `entry.py check GOLD`. Say the status in one line.
3. To wait for it, run `entry.py watch GOLD --until 22:00` in the background,
   or `entry.py check GOLD --write` every 5 minutes. `watch` exits 0 on the
   trigger (and writes `trader/entry.json`) or 1 when the setup expires.
4. When it triggers, say the time and the price, and that nothing was placed.
   If the trigger is more than a bar old, say so: a late entry is a different trade.
5. Hand off to `/trader-exit` to set the stop and target BEFORE anything is bought.

## Rules

- Free Yahoo bars are unofficial and can lag. Say so when a minute matters.
- A signal is information, not an order, and not a promise.
- Long side only. If the user wants a short, say this pack plans longs only.
- One trigger per setup per day: the first close above.
- Breakouts right before a scheduled US release (16:30 / 17:30 Dubai data,
  22:00-23:00 Dubai Fed) often reverse. Say so if one is close.

## Safety

- Education and tooling, not financial advice.
- Nothing in this pack places an order. The user places it themselves in their own broker's app
  (MT4/MT5, cTrader, a futures platform...), and only after trader-risk passed that exact order today.
- Gold and silver CFDs and futures are leveraged: losses can exceed what you planned if a stop gaps.
