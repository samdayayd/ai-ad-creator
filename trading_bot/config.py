"""
Configuration for the trading bot. Edit the values below, or override them
with environment variables (see .env.example).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# BROKER / MODE
# ---------------------------------------------------------------------------
# "paper"  -> trades against Alpaca's simulated paper-trading account (fake money, real market data)
# "live"   -> trades with real money in your real Alpaca account
#
# IMPORTANT: This defaults to "paper" on purpose. Run the bot in paper mode for
# at least a few trading days and confirm the logs, P&L tracking, and stop-loss
# orders all behave the way you expect BEFORE switching to "live". Flipping this
# one flag is the only thing that changes.
ALPACA_MODE = os.getenv("ALPACA_MODE", "paper")  # "paper" or "live"

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")

# ---------------------------------------------------------------------------
# UNIVERSE
# ---------------------------------------------------------------------------
# Symbols the bot is allowed to trade. Keep this small and liquid while testing.
SYMBOLS = ["AAPL", "MSFT", "SPY"]

# ---------------------------------------------------------------------------
# RISK MANAGEMENT  (this is the core of "low risk" — do not disable these)
# ---------------------------------------------------------------------------
# Bot stops opening new trades for the day once profit hits this amount.
MAX_DAILY_PROFIT_USD = 100.0

# Bot stops opening new trades for the day if losses hit this amount.
# Kept smaller than the profit target on purpose (tighter downside than upside).
MAX_DAILY_LOSS_USD = 50.0

# Max % of account equity risked on any single trade (used to size positions).
RISK_PER_TRADE_PCT = 0.01  # 1%

# Stop-loss and take-profit, as a % move from entry price.
STOP_LOSS_PCT = 0.015     # 1.5% below entry
TAKE_PROFIT_PCT = 0.03    # 3% above entry

# Never let a single position exceed this fraction of account equity,
# regardless of what the risk-per-trade calculation says.
MAX_POSITION_PCT_OF_EQUITY = 0.20  # 20%

# Max number of positions open at once.
MAX_OPEN_POSITIONS = 3

# ---------------------------------------------------------------------------
# NEWS / SENTIMENT FILTER
# ---------------------------------------------------------------------------
# Look back this many hours of news before allowing a buy.
NEWS_LOOKBACK_HOURS = 24

# Minimum number of recent headlines required to even consider a symbol.
# If a symbol has zero recent news, the bot treats it as "unknown" and skips it
# rather than assuming it's safe.
MIN_HEADLINES_REQUIRED = 1

# Compound sentiment score threshold (VADER scale: -1 very negative to +1 very positive).
# Trades are only allowed if the average sentiment is at or above this.
MIN_SENTIMENT_SCORE = -0.05  # roughly "not clearly negative"

# ---------------------------------------------------------------------------
# STRATEGY (simple trend + momentum filter, combined with the news gate above)
# ---------------------------------------------------------------------------
SMA_FAST = 20
SMA_SLOW = 50
RSI_PERIOD = 14
RSI_OVERSOLD = 40   # only consider buying when RSI is below this (avoid chasing)
RSI_OVERBOUGHT = 70  # avoid buying when RSI shows overbought conditions

# ---------------------------------------------------------------------------
# TIMING
# ---------------------------------------------------------------------------
LOOP_INTERVAL_SECONDS = 300  # check every 5 minutes during market hours

# ---------------------------------------------------------------------------
# STATE / LOGGING
# ---------------------------------------------------------------------------
STATE_FILE = "bot_state.json"
LOG_FILE = "trading_bot.log"
