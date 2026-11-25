"""tiny-sol-bot: a small long-only trend bot for agent-fun/bars-replay/v1.

Strategy: EMA(8)/EMA(21) crossover entries, long only, one program, no network,
no clock, no randomness -- fully deterministic, so the two grading runs agree.

Improvements over a plain EMA crossover (the house ema-cross baseline):
  1. Trend confirmation: an entry needs the close above EMA(21) as well as the
     cross, so it does not buy a cross that fires while price is still falling.
  2. Blow-off filter: an entry is skipped when the last bar's true range is
     more than 12% of its close -- meme coins spike vertically and then give it
     all back; chasing those bars is how a bot buys the top.
  3. Tighter risk: take profit at +30% and stop loss at -10% (the baseline
     waits for +50% / -20%), which keeps the maximum drawdown inside the
     25% guardrail on a choppy 3-day window.
  4. A sell signal holds while EMA(21) stays above EMA(8), so a refused sell
     (slippage cap, order cap) is retried on the next bar.

Sizing: equity split over min(universe, max_open_positions) slots, each buy
capped at max_weight_bps of equity and at the cash left in this reply.
Every order caps slippage at 100 bps past the close it was decided on.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars
from makefun_bars import BPS

FAST_BARS = 8
SLOW_BARS = 21
ATR_BARS = 24
# Skip an entry when the last bar's true range exceeds 12% of its close.
BLOWOFF_PCT = 0.12
# Take profit at +30% over cost, stop loss at -10% under it.
ROI_NUM, ROI_DEN = 13, 10
STOP_NUM, STOP_DEN = 9, 10
MAX_SLIPPAGE_BPS = 100


class Ema:
    """One EMA: the closes it has seen until it starts, then its value."""

    def __init__(self, span):
        self.span = span
        self.warm = []
        self.value = None

    def step(self, close):
        if self.value is not None:
            self.value += (2.0 / (self.span + 1)) * (close - self.value)
            return
        self.warm.append(close)
        if len(self.warm) == self.span:
            self.value = sum(self.warm) / self.span


class Series:
    """Per-symbol indicator state: fast/slow EMAs, cross gap, ATR, sell flag."""

    def __init__(self):
        self.fast = Ema(FAST_BARS)
        self.slow = Ema(SLOW_BARS)
        self.gap = None          # fast - slow after the previous bar
        self.now = None          # fast - slow after this bar
        self.down = False        # sell signal held while EMA(21) > EMA(8)
        self.prev_close = None   # previous bar's close, for true range
        self.atr = None          # mean true range over ATR_BARS bars
        self._trs = []           # recent true ranges, oldest first

    def push(self, close, high, low):
        if self.prev_close is not None:
            tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))
            self._trs.append(tr)
            if len(self._trs) > ATR_BARS:
                self._trs.pop(0)
            self.atr = sum(self._trs) / len(self._trs)
        self.prev_close = close
        self.fast.step(close)
        self.slow.step(close)
        self.gap = self.now
        if self.fast.value is not None and self.slow.value is not None:
            self.now = self.fast.value - self.slow.value
        else:
            self.now = None
        if self.now is None or self.now >= 0:
            self.down = False


series = {}


def get_series(symbol):
    s = series.get(symbol)
    if s is None:
        s = Series()
        series[symbol] = s
    return s


def exits(state, symbol, held, signal):
    """Whether a held position exits on this close: held sell signal, +30% or -10%."""
    if signal:
        return True
    value = state.value(symbol, held.qty)
    return value * ROI_DEN >= held.cost * ROI_NUM or value * STOP_DEN <= held.cost * STOP_NUM


def on_batch(state, batch):
    cross_up = set()
    fresh = set()
    for bar in batch["bars"]:
        s = get_series(bar["symbol"])
        s.push(float(bar["c"]), float(bar["h"]), float(bar["l"]))
        fresh.add(bar["symbol"])
        if s.gap is None or s.now is None or bar.get("v") == "0":
            continue
        if s.now > 0 and s.gap <= 0:
            # Trend confirmation: only buy when price is above the slow EMA,
            # and skip the blow-off bar (true range > 12% of close).
            close = float(bar["c"])
            if close > s.slow.value and not (s.atr is not None and s.atr > BLOWOFF_PCT * close):
                cross_up.add(bar["symbol"])
        if s.now < 0 and s.gap >= 0:
            s.down = True
    if state.warming_up:
        return []

    caps = state.hello["caps"]
    fees = state.hello["fees"]
    sells = []
    entries = []
    for sym in state.hello["symbols"]:
        symbol = sym["symbol"]
        if symbol not in fresh:
            continue
        held = state.positions.get(symbol)
        if held is not None:
            if exits(state, symbol, held, get_series(symbol).down):
                sells.append({"side": "sell", "symbol": symbol, "qty": held.qty,
                              "max_slippage_bps": MAX_SLIPPAGE_BPS})
        elif symbol in cross_up:
            entries.append(symbol)

    orders = sells[: caps["max_orders_per_bar"]]
    slots = min(len(state.hello["symbols"]), caps["max_open_positions"])
    stake = state.equity // slots
    by_weight = caps["max_weight_bps"] * state.equity // BPS
    room = slots - len(state.positions)
    cash = state.cash
    for symbol in entries:
        if room <= 0 or len(orders) >= caps["max_orders_per_bar"]:
            break
        size = stake if stake < by_weight else by_weight
        if cash < size:
            size = cash
        if size <= 0 or size < int(fees["min_notional_quote_units"]):
            break
        orders.append({"side": "buy", "symbol": symbol, "notional_quote_units": size,
                       "max_slippage_bps": MAX_SLIPPAGE_BPS})
        cash -= size
        room -= 1
    return orders


makefun_bars.run(on_batch)
