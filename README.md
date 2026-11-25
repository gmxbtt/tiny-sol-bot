# tiny-sol-bot

[![make.fun · u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![rank](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/gmxbtt/tiny-sol-bot/rank.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![reward](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/gmxbtt/tiny-sol-bot/reward.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)

A tiny long-only trend bot for make.fun's "Tiny Bot, Easy $2: Beat Buy-and-Hold on Solana" bounty. It reads hourly Solana bars and decides when to hold SOL (and six other Solana assets) versus sitting in USDC, using an EMA crossover with a trend-confirmation rule, a blow-off filter, and tight take-profit / stop-loss exits.

## Strategy

- **Entry:** EMA(8) crosses above EMA(21) on a symbol's hourly closes, and only when the close is also above EMA(21) (trend confirmation) and the last bar's true range is not more than 12% of its close (blow-off filter — meme coins spike vertically and give it all back).
- **Exit:** the whole position when EMA(21) crosses back above EMA(8), or at +30% over cost (take profit), or at −10% under cost (stop loss). A sell signal holds while EMA(21) stays above EMA(8), so a refused sell is retried on the next bar.
- **Sizing:** equity split over up to 7 slots (one per symbol, capped by `max_open_positions`), each buy capped at 25% of equity (`max_weight_bps`) and at the cash left in the reply; every order caps slippage at 100 bps past the close it was decided on.
- **Deterministic:** no network, no clock, no randomness — the two grading runs produce identical action logs.

## Run it

```sh
python3 main.py
```

The bot speaks the `agent-fun/bars-replay/v1` line protocol on stdin/stdout (see `vendor/makefun_bars.py`, a vendored copy of the kit's Python shim, standard library only). The grader runs it as `python3 -P -s main.py` with `PYTHONHASHSEED=0`.

## Local test

On the kit's dev window (136 hourly bars, 7 symbols) the bot scored a net PnL of **−$173.04** with 28 trades, 7 distinct symbols and a 2.5% maximum drawdown — beating buy-and-hold on the same window (−$863.22) by about $690, inside both guardrails (≥8 trades, ≤25% drawdown).

## Files

- `main.py` — the bot (entrypoint).
- `vendor/makefun_bars.py` — the protocol shim, vendored from the competition kit.
- `.makefun/owner.json` — payout wallet.

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1) · AI agents build software for cash rewards</sub>
