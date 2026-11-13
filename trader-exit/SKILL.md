---
name: trader-exit
description: >-
  Exit Planner for gold and silver. Sets the stop and the target BEFORE you
  enter, so you know when to get out. Reads the trigger from /trader-entry
  (or a price you give), puts the stop at the opening-range midpoint by
  default (or the range low, a price, a percent, or K x ATR), the target at
  2R, and the flat-by time at 23:15 Dubai, and writes trader/plan.json for
  the replay, sizing, risk and alert skills. Long side only. Use when the user
  says "where's my stop", "set my stop and target", "plan the exit", "how
  much am I risking an ounce", or right after /trader-entry triggers.
argument-hint: "[--stop or-mid|or-low|price:X|pct:X|atr:K] [--target 2R|1R|price:X]"
---

> **Gold and silver edition.** Prices are COMEX futures from Yahoo (GC=F for gold, SI=F for silver), in US dollars per ounce. Type GOLD, SILVER, XAUUSD or XAGUSD; the scripts translate. All times are Dubai (UTC+4). The day-trading session is 12:00 to 23:30 Dubai (London open to late New York). Your broker's spot or CFD price can differ from the futures by a few dollars.

# trader-exit

The exit is decided before the entry, while you are calm. The stop is where
the idea is wrong; the target is a multiple of that risk; flat-by is the
time you are out no matter what.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan                          # trader/entry.json: midpoint stop, 2R target
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --stop or-mid --target 1.5R --write
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --stop atr:1.5           # needs the session's bars (Yahoo or --offline)
python3 "${CLAUDE_SKILL_DIR}/exit.py" plan --symbol GOLD --entry 4075 --or-high 4072.40 --or-low 4061.80
python3 "${CLAUDE_SKILL_DIR}/exit.py" show                          # the current trader/plan.json
```

Other flags: `--flat-by 23:15`, `--json`, `--now "2026-11-13 12:35"` (Dubai),
`--offline PATH`, `--from trader/entry.json`.

## Stops and targets

| stop | where it goes |
| --- | --- |
| `or-mid` | the opening-range midpoint (default for an opening-range breakout) |
| `or-low` | the opening-range low: wider, so fewer ounces for the same max loss |
| `price:X` | your price |
| `pct:X` | X percent under the entry |
| `atr:K` | K times the 14-bar ATR under the entry, on the session's bars so far |

- The stop rounds away from the entry to the cent. Risk an ounce = entry
  minus stop. Target = entry + R x risk (`2R` default; `1R`, `1.5R`,
  `price:X` work too).
- Refused, with the reason: a stop at or above the entry, a target at or
  below it, a risk under 0.05 % of the price (about $2 on gold, $0.03 on
  silver: inside normal noise and the spread), an entry that has not triggered.
- Flat by 23:15 Dubai by default (`flat_by` in the config), before the 23:30
  session end. No overnight holds: swaps and the 01:00-02:00 Dubai futures
  break are out of scope.

## Steps

1. Run it right after `/trader-entry` triggers (`exit.py plan --write`).
2. Read back the entry, the stop and its rule, the target, the risk an
   ounce, reward:risk and flat-by.
3. If the user trades a CFD whose price differs from the futures, tell them
   to keep the same DISTANCES (risk and reward in dollars an ounce) from
   their own fill, not the exact prices.
4. If it refuses, say the reason and the fix. Never loosen anything on your own.
5. Hand off to `/trader-timemachine`, then `/trader-budget`. Offer `/trader-alerts`.

## Safety

- Education and tooling, not financial advice. A stop is a plan, not a guarantee:
  around CPI, payrolls or a Fed decision gold can jump straight through it.
- Nothing in this pack places an order. The user places it themselves in their own broker's app
  (MT4/MT5, cTrader, a futures platform...), and only after trader-risk passed that exact order today.
