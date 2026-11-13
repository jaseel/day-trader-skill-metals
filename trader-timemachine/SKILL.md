---
name: trader-timemachine
description: >-
  Time Machine for gold and silver. Replays the trade before you risk a
  dollar: takes the plan from /trader-exit and plays the rest of the session
  10,000 times from the metal's own 5-minute bars over roughly the last 60
  sessions (12:00-23:30 Dubai), then runs the same rule on every one of those
  real sessions. Reports target first, stop first, still open at the
  flat-by time, the price spread, average R and a verdict on whether the
  odds beat break-even for the target's R. Use when the user says "replay
  this", "backtest it", "what are the odds", "would this have worked", "run
  the time machine", or after /trader-exit and before /trader-budget.
argument-hint: "[path to plan.json, or GOLD | SILVER]"
---

> **Gold and silver edition.** Prices are COMEX futures from Yahoo (GC=F for gold, SI=F for silver), in US dollars per ounce. Type GOLD, SILVER, XAUUSD or XAGUSD; the scripts translate. All times are Dubai (UTC+4). The day-trading session is 12:00 to 23:30 Dubai (London open to late New York). Your broker's spot or CFD price can differ from the futures by a few dollars.

# trader-timemachine

One question: if today plays out like this metal's last ~60 sessions, how
often does the stop come first? It is a simulation built from its own recent
bars, not a forecast.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run                    # trader/plan.json, 10,000 replays, seed 19
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --until 23:15 --write   # end at flat-by; save trader/timemachine.json
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --json
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" run --symbol GOLD --date 2026-11-13 \
    --entry 4075 --stop 4067 --target 4091 --entry-time 12:30
python3 "${CLAUDE_SKILL_DIR}/timemachine.py" chart --from           # ASCII fan chart of the saved run
```

Other flags: `--seed N`, `--replays N`, `--offline PATH`, `--now` (Dubai).

## How it works

1. Pulls ~60 days of 5-minute bars (Yahoo, `range=60d`) and keeps the full
   12:00-23:30 Dubai sessions (138 bars) before the plan's date. Half days
   (US-holiday early closes) and sessions missing more than 10 bars are left
   out; small gaps are filled flat, and it says how many.
2. 10,000 replays: from the entry bar on, each bar is drawn from the same
   time of day (+-2 bars) in a past session, scaled to today's price.
3. History: the same rule on each real session.
4. Verdict: at 2R the target must come first in 33 % of the replays that
   hit a side to break even; it says how far above or below that the run is.

## Steps

1. Run `timemachine.py run --until <flat_by>` after `/trader-exit`.
2. Repeat the printed numbers and the verdict line as they are. Say the seed.
3. If the verdict leans to the stop, say it plainly before sizing.
4. Hand off to `/trader-budget`.

## Rules

- Every number comes from the run. Never round a coin flip up into an edge.
- The pool is ordinary days. CPI, payrolls, Fed and geopolitical shock days
  behave differently; if today is one, say the replay understates the risk.
- Simulated odds are not predictions and not promises.

## Safety

- Education and tooling, not financial advice.
- Nothing in this pack places an order. The user places it themselves in their own broker's app
  (MT4/MT5, cTrader, a futures platform...), and only after trader-risk passed that exact order today.
