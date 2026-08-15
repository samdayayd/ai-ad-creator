"""
Main trading bot.

Flow, once per loop iteration, for each symbol:
  1. Check daily profit/loss caps -> halt if hit.
  2. Pull recent price bars -> run strategy -> buy/avoid/hold signal.
  3. If signal is "buy": check real news sentiment for the symbol.
  4. If news is not clearly negative: size the position, place a bracket
     order (entry + stop-loss + take-profit all at once).
  5. Log everything.

Run:
    python bot.py                 # uses ALPACA_MODE from config.py / .env
    python bot.py --mode paper    # force paper trading regardless of config
    python bot.py --mode live     # force live trading (will ask you to confirm)
    python bot.py --once          # run a single pass instead of looping (good for cron)
"""

import argparse
import logging
import sys
import time
from datetime import datetime

import config
from news_checker import NewsChecker
from risk_manager import RiskManager
from strategy import generate_signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("trading_bot")


def build_clients(mode: str):
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.historical.news import NewsClient

    if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
        logger.error("Missing ALPACA_API_KEY / ALPACA_SECRET_KEY. Set them in your .env file.")
        sys.exit(1)

    trading_client = TradingClient(
        config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, paper=(mode == "paper")
    )
    data_client = StockHistoricalDataClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY)
    news_client = NewsClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY)
    return trading_client, data_client, news_client


def get_recent_bars(data_client, symbol: str, lookback_days: int = 90):
    import pandas as pd
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from datetime import timedelta, timezone

    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now(timezone.utc) - timedelta(days=lookback_days),
    )
    bars = data_client.get_stock_bars(req)
    df = bars.df
    if df.empty:
        return pd.DataFrame(columns=["close"])
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level=0)
    return df


def place_bracket_buy(trading_client, symbol: str, qty: int, entry_hint: float,
                       stop_loss: float, take_profit: float):
    from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        order_class=OrderClass.BRACKET,
        take_profit=TakeProfitRequest(limit_price=take_profit),
        stop_loss=StopLossRequest(stop_price=stop_loss),
    )
    return trading_client.submit_order(order)


def run_cycle(trading_client, data_client, news_checker, risk_manager):
    allowed, reason = risk_manager.trading_allowed_today()
    if not allowed:
        logger.info(f"Trading halted for today: {reason}")
        return

    account = trading_client.get_account()
    equity = float(account.equity)

    open_positions = trading_client.get_all_positions()
    open_symbols = {p.symbol for p in open_positions}

    if len(open_positions) >= config.MAX_OPEN_POSITIONS:
        logger.info(f"Max open positions ({config.MAX_OPEN_POSITIONS}) reached, skipping new entries.")
        return

    for symbol in config.SYMBOLS:
        if symbol in open_symbols:
            logger.info(f"[{symbol}] Already have an open position, skipping.")
            continue

        bars_df = get_recent_bars(data_client, symbol)
        signal, diag = generate_signal(
            bars_df, config.SMA_FAST, config.SMA_SLOW,
            config.RSI_PERIOD, config.RSI_OVERSOLD, config.RSI_OVERBOUGHT,
        )
        logger.info(f"[{symbol}] strategy signal={signal} diagnostics={diag}")

        if signal != "buy":
            continue

        # --- mandatory real-news check before any buy ---
        news_ok, news_reason, sentiment, headline_count = news_checker.is_safe_to_buy(symbol)
        logger.info(f"[{symbol}] news check: allowed={news_ok} reason='{news_reason}'")
        if not news_ok:
            continue

        entry_price = diag["close"]
        stop_loss = risk_manager.stop_loss_price(entry_price)
        take_profit = risk_manager.take_profit_price(entry_price)
        qty = risk_manager.calculate_position_size(equity, entry_price, stop_loss)

        if qty <= 0:
            logger.info(f"[{symbol}] Position size computed as 0, skipping (equity too low or risk too tight).")
            continue

        try:
            order = place_bracket_buy(trading_client, symbol, qty, entry_price, stop_loss, take_profit)
            logger.info(
                f"[{symbol}] BUY submitted: qty={qty} entry~{entry_price} "
                f"stop_loss={stop_loss} take_profit={take_profit} order_id={order.id}"
            )
        except Exception as e:
            logger.error(f"[{symbol}] Order submission failed: {e}")


def market_is_open(trading_client):
    clock = trading_client.get_clock()
    return clock.is_open


def confirm_live_mode():
    print("\n" + "=" * 70)
    print("WARNING: You are about to run this bot in LIVE mode with REAL MONEY.")
    print(f"  Max daily profit target : ${config.MAX_DAILY_PROFIT_USD}")
    print(f"  Max daily loss limit    : ${config.MAX_DAILY_LOSS_USD}")
    print(f"  Risk per trade          : {config.RISK_PER_TRADE_PCT * 100:.1f}% of equity")
    print(f"  Stop loss / take profit : {config.STOP_LOSS_PCT*100:.1f}% / {config.TAKE_PROFIT_PCT*100:.1f}%")
    print(f"  Symbols                 : {', '.join(config.SYMBOLS)}")
    print("This is not financial advice, and past strategy performance is not a")
    print("guarantee of future results. Recommended: run in paper mode first.")
    print("=" * 70)
    resp = input("Type LIVE to confirm and continue, or anything else to abort: ")
    return resp.strip() == "LIVE"


def main():
    parser = argparse.ArgumentParser(description="News-filtered, risk-managed trading bot.")
    parser.add_argument("--mode", choices=["paper", "live"], default=None,
                         help="Override ALPACA_MODE from config/.env")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    args = parser.parse_args()

    mode = args.mode or config.ALPACA_MODE

    if mode == "live":
        if not confirm_live_mode():
            print("Aborted. No orders were placed.")
            sys.exit(0)

    logger.info(f"Starting trading bot in {mode.upper()} mode.")

    trading_client, data_client, news_client = build_clients(mode)
    news_checker = NewsChecker(
        news_client, config.NEWS_LOOKBACK_HOURS,
        config.MIN_HEADLINES_REQUIRED, config.MIN_SENTIMENT_SCORE,
    )
    risk_manager = RiskManager(config, config.STATE_FILE)

    while True:
        try:
            if market_is_open(trading_client):
                run_cycle(trading_client, data_client, news_checker, risk_manager)
            else:
                logger.info("Market is closed, waiting.")
        except Exception as e:
            logger.error(f"Cycle failed: {e}", exc_info=True)

        if args.once:
            break
        time.sleep(config.LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
