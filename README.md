# Day Trader Skill: Gold and Silver edition

8 Claude skills for day trading gold and silver (XAUUSD, XAGUSD): scan for
setups, track the news, time every entry and exit, replay the trade 10,000
times, size it in lots with your leverage, check it against your rules, and
ring the alerts.

Adapted from [Shakir C's India (NSE) edition](https://github.com/mshakirc/day-trader-skill-india),
itself a patched copy of [Jake Schincariol's day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT).

- **Instruments:** GOLD and SILVER. XAUUSD, XAGUSD, XAU, XAG, GC and SI also
  work, and so do MGC and SIL (the micro futures).
- **Prices:** COMEX futures from Yahoo Finance (GC=F, SI=F), in US dollars an
  ounce. A spot or CFD quote from your broker can differ by a few dollars.
  Keep the stop and target distances and apply them to your own fill.
- **Clock:** Dubai (UTC+4, no daylight saving).
- **Session:** 12:00 to 23:30 Dubai, from the London open (winter time) to the late New York afternoon.
  - Opening range: 12:00 to 12:15.
  - Entries: 12:30 to 22:00.
  - Flat by 23:15.
  - Every one of these times can be changed in `trader/config.json`.
- **Calendar:** weekends and the CME metals closures (New Year, Good Friday,
  Christmas) are closed. US holidays are treated as a 21:00 Dubai early close.
- **Sizing:** in ounces, in whole lot steps, shown as lots. One lot is
  100 oz of gold or 5,000 oz of silver (the CFD standard), and you can change
  that. Margin is the notional divided by your leverage.
- **News:** gold and silver price headlines (Google News), tagged for the
  Fed, inflation, jobs, the dollar and yields, geopolitics, central banks,
  ETF flows, demand and supply.
- **No order is ever placed.** You place your own order in MT4/MT5, cTrader
  or your futures platform.

Not financial advice. A scan, a replay or a signal is not a reason to buy anything.

## Install

In Claude Code:

```
/plugin marketplace add <path or git URL of this folder>
/plugin install day-trader-skill-metals@day-trader-skill-metals
```

Or copy the skill folders:

```bash
cp -r trader-* ~/.claude/skills/
```

The tools need Python 3.8 or newer and internet access to Yahoo Finance and
Google News. There's nothing to pip install.

## The eight

| command | job |
| --- | --- |
| `/trader-scanner` | Daily-close setups before 12:00, and opening-range breakouts after 12:20. |
| `/trader-news` | New gold and silver headlines, today's move, and what's driving it. |
| `/trader-entry` | Watches bar by bar and calls the first close above the range high (or your level). |
| `/trader-exit` | Stop (range midpoint by default), target (2R), flat by 23:15. Set before the entry. |
| `/trader-timemachine` | 10,000 replays from the metal's own last ~60 sessions, plus the same rule on each real session. |
| `/trader-budget` | Lots and ounces that fit your max loss, margin and cash. |
| `/trader-risk` | PASS or BLOCK against your max loss, daily loss, trade count, reward:risk, entry window and margin. |
| `/trader-alerts` | Rings on the stop, the target and at 23:15 to close what is still open. |

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> you place it in your broker's app
alerts: stop, target, flat by 23:15                                (while it is open)
```

Everything lands in a `trader/` folder in your project. Start your rules by
copying `trader-budget/config.example.json` to `trader/config.json`, then set
your budget, leverage, contract size and max loss.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests build synthetic gold and silver bars with a planted
opening-range breakout. They aren't real prices. The tests run the whole
chain from scan to alerts against those bars. Live data has not been
tested from the machine this edition was built on, which had no access to
Yahoo, so check the first live run against your broker's chart.

## Fine print

**Not financial advice.** This is software that reads public data and does
arithmetic. It doesn't know your situation and it can't see the future.
Most retail traders of leveraged gold and silver CFDs lose money. A stop is
an order, not a guarantee: gold can gap through it on CPI, payrolls or a Fed
decision. Decide for yourself, and talk to a licensed adviser if you need advice.

**Nothing places an order.** This pack only reads, plans and checks.

License: MIT (see LICENSE). The original copyright stays with Jake Schincariol.
