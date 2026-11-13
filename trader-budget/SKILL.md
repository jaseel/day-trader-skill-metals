---
name: trader-budget
description: >-
  Budget Manager for gold and silver. Sizes every trade to your account and
  your max loss per trade, in lots and ounces. Reads the plan from
  /trader-exit (entry, stop, target), finds the largest size in whole lot
  steps that fits four limits (max loss per trade, position cap, max order
  notional, cash after your buffer, with your broker's leverage), says which
  limit decided it, and writes ONE bracket order to trader/orders.json. A
  stop too far for your max loss is a plain refusal. Nothing is placed. Use
  when the user says "how many lots", "size this trade", "how much gold
  should I buy", "I only want to risk $100 a trade", "my leverage is 1:20",
  "set my rules", or after /trader-exit writes a plan.
argument-hint: "[budget in dollars]"
---

> **Gold and silver edition.** Prices are COMEX futures from Yahoo (GC=F for gold, SI=F for silver), in US dollars per ounce. Type GOLD, SILVER, XAUUSD or XAGUSD; the scripts translate. All times are Dubai (UTC+4). The day-trading session is 12:00 to 23:30 Dubai (London open to late New York). Your broker's spot or CFD price can differ from the futures by a few dollars.

# trader-budget

The stop decides the size: the further away the stop, the fewer ounces. The
budget manager turns "buy gold at 4,075, stop 4,067" into "buy 0.12 lots",
inside rules the user sets once.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/size.py"                        # trader/plan.json + trader/config.json
python3 "${CLAUDE_SKILL_DIR}/size.py" --write                # write trader/orders.json
python3 "${CLAUDE_SKILL_DIR}/size.py" --budget 5000 --write  # override the budget
python3 "${CLAUDE_SKILL_DIR}/size.py" --limit --write        # a limit order at the plan's entry
python3 "${CLAUDE_SKILL_DIR}/size.py" --json
```

## Your rules: trader/config.json

Start from `config.example.json` in this folder (copy it to `trader/config.json`
and ask the user for their numbers). Money is in US dollars.

| key | example | what |
| --- | --- | --- |
| `budget` | 10000 | account equity |
| `leverage` | 20 | the broker's leverage (1:20). 1 = no leverage. Only changes how much margin a trade ties up, never the dollar risk |
| `contract_oz` | GOLD 100, SILVER 5000 | ounces in 1 lot. CFD standard: XAUUSD 100 oz, XAGUSD 5,000 oz. Futures: GC 100, MGC 10, SI 5,000, SIL 1,000 |
| `lot_step` | 0.01 | smallest lot increment (futures: 1) |
| `max_loss_per_trade_usd` | 100 | dollars lost if the stop fills |
| `max_daily_loss_usd` | 300 | for trader-risk |
| `max_position_pct` | 100 | margin cap, % of the budget |
| `max_order_usd` | 1000000 | notional cap per order |
| `cash_buffer_pct` | 0 | % of the budget never used |
| `min_reward_risk` | 1.5 | trader-risk blocks anything under it |
| `no_entries_before` / `no_entries_after` / `flat_by` | 12:30 / 22:00 / 23:15 | Dubai |

Ask for the broker's contract size and leverage if the user has not said:
they differ between brokers, and a wrong `contract_oz` mis-sizes by 100x.

## The math

Size is in ounces, in whole lot steps (gold 0.01 lot = 1 oz, silver 0.01 lot = 50 oz):

| limit | ounces |
| --- | --- |
| max loss | `max_loss_per_trade_usd` / risk an ounce (entry minus stop) |
| position cap | budget x `max_position_pct` / (entry / leverage) |
| max order | `max_order_usd` / entry |
| cash | (budget, or portfolio cash, minus the buffer) / (entry / leverage) |

The smallest wins, rounded DOWN to a lot step. Max loss = ounces x risk an
ounce. Margin = ounces x entry / leverage. If even one step risks more than
the max loss, there is no order: say skip it, or plan a closer stop.

## Steps

1. Make sure `trader/config.json` exists with the user's budget, leverage,
   contract size and max loss.
2. Run `size.py --write`. Say the size in lots and ounces, which limit
   decided it, the max loss at the stop and the margin.
3. Remind the user: their broker's quote may differ from COMEX by a few
   dollars, so set the stop and target the same distance from their own fill.
4. Hand off to `/trader-risk`.

## Safety

- Education and tooling, not financial advice.
- Leverage multiplies exposure: 0.5 lots of gold is 50 oz, about $200,000 of
  metal. The max-loss rule is what protects the account, not the margin.
- Nothing in this pack places an order. The user places it themselves in their own broker's app
  (MT4/MT5, cTrader, a futures platform...), and only after trader-risk passed that exact order today.
