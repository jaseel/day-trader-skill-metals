---
name: trader-risk
description: >-
  Risk Manager for gold and silver. Checks every proposed order in
  trader/orders.json against your rules before you place it: max loss per
  trade, max daily loss, trades per day, reward:risk, the Dubai entry window
  (12:30-22:00), COMEX holidays, position size, margin against your cash
  (with leverage), and a stop on the right side. Each order gets PASS or
  BLOCK with the reasons and the numbers, recorded in
  trader/state/risk.json. Use when the user says "check this trade", "is
  this within my rules", "risk check", "can I take this", or after
  /trader-budget writes an order and before the user places it.
argument-hint: "[path to orders.json]"
---

> **Gold and silver edition.** Prices are COMEX futures from Yahoo (GC=F for gold, SI=F for silver), in US dollars per ounce. Type GOLD, SILVER, XAUUSD or XAGUSD; the scripts translate. All times are Dubai (UTC+4). The day-trading session is 12:00 to 23:30 Dubai (London open to late New York). Your broker's spot or CFD price can differ from the futures by a few dollars.

# trader-risk

The last gate before a trade. It does not judge whether the trade is good;
it checks that it fits the rules the user wrote down when they were calm.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/check.py"                           # trader/ files; writes trader/state/risk.json
python3 "${CLAUDE_SKILL_DIR}/check.py" --json
python3 "${CLAUDE_SKILL_DIR}/check.py" --no-write                # look without recording
python3 "${CLAUDE_SKILL_DIR}/check.py" --now "2026-11-13 12:40"  # pin the clock (Dubai)
```

Exit code 0 when every order passes, 1 when any is blocked.

## What it reads

| file | what |
| --- | --- |
| `trader/orders.json` | from `/trader-budget`: qty in ounces, lots, entry, stop, target |
| `trader/config.json` | the rules (see trader-budget), including `leverage` |
| `trader/portfolio.json` | optional: `cash` and positions |
| `trader/prices.json` | optional: fresh quotes from `/trader-alerts` |
| `trader/state/broker.json` | what the user placed today (they tell you; record it) |

## What blocks an entry

| check | blocks when |
| --- | --- |
| loss | ounces x (entry minus stop) over `max_loss_per_trade_usd` |
| daily loss | today's max losses at the stops, plus this one, over `max_daily_loss_usd` |
| trades | `max_trades_per_day` entries already placed today |
| reward:risk | under `min_reward_risk` |
| stop | no stop, or a stop on the wrong side of the entry |
| window | before `no_entries_before` (12:30) or after `no_entries_after` (22:00) Dubai; weekends; COMEX holidays (Good Friday, Christmas, New Year); after a 21:00 early close on US holidays |
| cash | the margin (notional / leverage) would dip into the buffer or exceed cash |
| position | margin over `max_position_pct` of the account |
| size | notional over `max_order_usd` or under `min_order_usd` |
| format / asset | a malformed order, or a symbol it does not know |

The entry it measures from is the higher of the plan's entry and a fresh
price (under 15 minutes old) from `trader/prices.json`, so a stale plan
cannot understate the risk.

## Steps

1. Run `check.py`. Say PASS or BLOCK for each order with the numbers it printed.
2. For a BLOCK, give the reason and the fix (fewer lots, a closer stop, wait
   for the window, stop for the day). Never edit the rules to make it pass.
3. On PASS: say the user can place it themselves (lots, stop-loss and
   take-profit), and that nothing was placed. When they say they placed it,
   record it in `trader/state/broker.json` so the daily limits count it.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order. The user places it themselves in their own broker's app
  (MT4/MT5, cTrader, a futures platform...), and only after trader-risk passed that exact order today.
- Gold and silver CFDs and futures are leveraged: losses can exceed what you planned if a stop gaps.
