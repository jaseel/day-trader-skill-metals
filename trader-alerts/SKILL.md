---
name: trader-alerts
description: >-
  Price Alerts for gold and silver. Rings when a price, a stop, a target or
  a time hits. Turns the trade plan into three alerts in one go (the stop,
  the target and "flat by close" at 23:15 Dubai), plus above / below levels,
  percent moves, any time of day and the 12:00 Dubai session open, each
  ringing once. Knows the session (12:00-23:30 Dubai), weekends and COMEX
  holidays, fetches free delayed quotes (Yahoo, GC=F and SI=F) and writes
  trader/prices.json for sizing and the risk check. Use when the user says
  "alert me when gold hits", "watch my stop", "watch my trade", "remind me
  to close by 23:15", "is the gold market open", "get me a gold price", or
  right after /trader-exit writes a plan.
argument-hint: "[GOLD | SILVER] [price]"
---

> **Gold and silver edition.** Prices are COMEX futures from Yahoo (GC=F for gold, SI=F for silver), in US dollars per ounce. Type GOLD, SILVER, XAUUSD or XAGUSD; the scripts translate. All times are Dubai (UTC+4). The day-trading session is 12:00 to 23:30 Dubai (London open to late New York). Your broker's spot or CFD price can differ from the futures by a few dollars.

# trader-alerts

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/alerts.py" clock                          # session open or closed, next open
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --from-plan                # stop, target, flat by close from trader/plan.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --opening-bell
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol GOLD --stop 4067
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol GOLD --target 4091
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --symbol SILVER --pct 2
python3 "${CLAUDE_SKILL_DIR}/alerts.py" add --at 23:15 --label "flat by close" --before-close
python3 "${CLAUDE_SKILL_DIR}/alerts.py" check                          # exit 0 = something rang
python3 "${CLAUDE_SKILL_DIR}/alerts.py" quote GOLD --write             # -> trader/prices.json
python3 "${CLAUDE_SKILL_DIR}/alerts.py" list
python3 "${CLAUDE_SKILL_DIR}/alerts.py" reset gold-plan-stop
```

`--now "2026-11-13 23:15"` pins the clock (Dubai); `--offline DIR` reads saved quotes.

## Rule types

| type | rings when | rings again |
| --- | --- | --- |
| `above` / `target` | price at or above `price` | after `reset`, or with `"rearm": true` |
| `below` / `stop` | price at or below `price` | same |
| `pct_move` | moved `pct` % from the previous settlement | once per day at most |
| `time` | the Dubai clock passed `at` on a trading day | once per trading day |
| `opening_bell` | the 12:00 Dubai session opened | once per trading day |

Plan alerts carry the plan's date, so yesterday's stop never rings today.
A `--before-close` time alert moves earlier on a US-holiday early close (21:00).

## Steps

1. After `/trader-exit`: `alerts.py add --from-plan`.
2. While the trade is open, run `alerts.py check` every few minutes (a
   scheduled task or a loop). Say what rang, plainly.
3. On "flat by close": tell the user to close whatever is still open
   themselves in their broker's app.

## Rules

- Quotes are free and delayed, and they are COMEX futures, not the user's
  CFD feed. The broker's own stop-loss and take-profit are what actually
  get them out; an alert is a second pair of eyes.
- An alert is information, not an order.

## Safety

- Education and tooling, not financial advice.
- Nothing in this pack places an order. The user places it themselves in their own broker's app
  (MT4/MT5, cTrader, a futures platform...), and only after trader-risk passed that exact order today.
