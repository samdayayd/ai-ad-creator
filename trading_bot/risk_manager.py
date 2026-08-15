"""
Risk management: position sizing, stop-loss/take-profit calculation, and
daily profit/loss caps. This module is the safety net for the whole bot --
it is intentionally conservative and does not get bypassed by the strategy
or news logic.
"""

import json
import logging
import os
from datetime import date

logger = logging.getLogger("trading_bot.risk")


class RiskManager:
    def __init__(self, config, state_file: str):
        self.config = config
        self.state_file = state_file
        self.state = self._load_state()

    # ---------------- persistence ----------------

    def _load_state(self):
        today = date.today().isoformat()
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                state = json.load(f)
            if state.get("date") != today:
                # new trading day -> reset daily counters, but a position
                # opened yesterday may still be open, so carry it forward
                state = self._fresh_state(today, carry_open_trades=state.get("open_trades", {}))
        else:
            state = self._fresh_state(today)
        self._save_state(state)
        return state

    def _fresh_state(self, today, carry_open_trades=None):
        return {
            "date": today,
            "realized_pnl_today": 0.0,
            "trades_today": 0,
            "halted": False,
            "halt_reason": "",
            "open_trades": carry_open_trades or {},
        }

    def _save_state(self, state=None):
        with open(self.state_file, "w") as f:
            json.dump(state or self.state, f, indent=2)

    # ---------------- daily limits ----------------

    def refresh_day(self):
        today = date.today().isoformat()
        if self.state.get("date") != today:
            self.state = self._fresh_state(today, carry_open_trades=self.state.get("open_trades", {}))
            self._save_state()

    def record_closed_trade_pnl(self, pnl: float):
        self.refresh_day()
        self.state["realized_pnl_today"] += pnl
        self.state["trades_today"] += 1
        self._check_daily_limits()
        self._save_state()

    # ---------------- open trade tracking ----------------
    # Used to reconcile realized P&L once a stop-loss/take-profit leg fills;
    # see bot.reconcile_closed_trades().

    def record_open_trade(self, symbol: str, order_id: str, qty: int, entry_price: float):
        self.state.setdefault("open_trades", {})[symbol] = {
            "order_id": str(order_id),
            "qty": qty,
            "entry_price": entry_price,
        }
        self._save_state()

    def get_open_trades(self):
        return dict(self.state.get("open_trades", {}))

    def forget_open_trade(self, symbol: str):
        self.state.setdefault("open_trades", {}).pop(symbol, None)
        self._save_state()

    def _check_daily_limits(self):
        pnl = self.state["realized_pnl_today"]
        if pnl >= self.config.MAX_DAILY_PROFIT_USD:
            self.state["halted"] = True
            self.state["halt_reason"] = f"Daily profit target reached (${pnl:.2f})"
            logger.info(self.state["halt_reason"])
        elif pnl <= -self.config.MAX_DAILY_LOSS_USD:
            self.state["halted"] = True
            self.state["halt_reason"] = f"Daily loss limit reached (${pnl:.2f})"
            logger.warning(self.state["halt_reason"])

    def trading_allowed_today(self):
        self.refresh_day()
        return not self.state["halted"], self.state.get("halt_reason", "")

    # ---------------- position sizing ----------------

    def calculate_position_size(self, equity: float, entry_price: float, stop_loss_price: float):
        """
        Sizes the position so that if the stop-loss is hit, the loss equals
        RISK_PER_TRADE_PCT of account equity -- capped so no single position
        exceeds MAX_POSITION_PCT_OF_EQUITY of the account.
        """
        risk_amount = equity * self.config.RISK_PER_TRADE_PCT
        per_share_risk = max(entry_price - stop_loss_price, 0.01)
        shares_by_risk = risk_amount / per_share_risk

        max_position_value = equity * self.config.MAX_POSITION_PCT_OF_EQUITY
        shares_by_cap = max_position_value / entry_price

        shares = int(min(shares_by_risk, shares_by_cap))
        return max(shares, 0)

    def stop_loss_price(self, entry_price: float):
        return round(entry_price * (1 - self.config.STOP_LOSS_PCT), 2)

    def take_profit_price(self, entry_price: float):
        return round(entry_price * (1 + self.config.TAKE_PROFIT_PCT), 2)
