# News-Filtered Risk-Managed Trading Bot

A US-stock trading bot for Alpaca that:

- Checks real financial news sentiment (via Alpaca's News API, which aggregates
  Benzinga, Business Wire, PR Newswire, GlobeNewswire, and other real sources)
  before placing any buy order, and refuses to buy if sentiment is negative or
  if there's no recent news to evaluate.
- Uses a transparent SMA-crossover + RSI strategy for entry signals (no black box).
- Sizes every position by risk (1% of equity per trade by default).
- Attaches a stop-loss and take-profit to every order automatically (Alpaca
  bracket orders — these live on the exchange side, not just in the bot).
- Stops opening new trades once daily profit hits **$100** or daily loss hits **$50**.
- Caps how many positions can be open at once and how large any one position can be.

## ⚠️ Read this before running

- **This is not financial advice, and I'm not a financial advisor.** This is a
  piece of software; it does not guarantee profit and can lose money, including
  in ways that look like bugs but are actually just how markets work.
- Trading involves real risk. Only risk money you can afford to lose.
- **Strongly recommended:** run in paper mode (the default) for at least a
  couple weeks first, and read the logs every day, before ever switching to live.
- No bot can monitor "every news platform" in existence. This one checks a real,
  live financial news aggregator — that's a meaningful filter, not a promise of
  omniscience. Markets can still move on news the feed hasn't picked up yet.
- Pattern Day Trading (PDT) rules apply to US accounts under $25,000 if you make
  4+ day trades in 5 business days — this bot doesn't currently enforce that limit,
  so keep an eye on your trade count if your account is under $25k.
- You are responsible for your own broker account, API keys, and tax reporting.

## Setup

1. Create a free Alpaca account: https://alpaca.markets/ — start with **Paper Trading** keys.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your API key/secret:
   ```
   cp .env.example .env
   ```
4. Review and adjust `config.py` — symbols, risk %, daily caps, stop-loss/take-profit %.
5. Run it:
   ```
   python bot.py                 # loops continuously during market hours
   python bot.py --once          # single pass, good for testing or cron
   ```

## Going live

When (and only when) you're satisfied with paper results:

1. Get **live** API keys from Alpaca (requires a funded brokerage account).
2. Update `.env`: set `ALPACA_MODE=live` and use your live keys.
3. Run `python bot.py`. It will print your current risk settings and require
   you to type `LIVE` to confirm before it places a single real order.

## Files

| File               | Purpose                                                |
|--------------------|---------------------------------------------------------|
| `bot.py`           | Main loop: ties strategy, news, and risk together       |
| `config.py`        | All tunable settings (risk %, symbols, thresholds)      |
| `strategy.py`      | SMA + RSI signal generation                              |
| `news_checker.py`  | Fetches + scores real news sentiment                     |
| `risk_manager.py`  | Position sizing, daily P&L tracking, trading halts       |
| `bot_state.json`   | Auto-generated daily P&L tracking (resets each day)      |
| `trading_bot.log`  | Full run log                                              |

## Tuning the "low risk, max $100/day" behavior

All in `config.py`:
- `MAX_DAILY_PROFIT_USD = 100` — bot stops trading for the day once hit.
- `MAX_DAILY_LOSS_USD = 50` — bot stops trading for the day if hit (downside capped tighter than upside).
- `RISK_PER_TRADE_PCT = 0.01` — risks 1% of account equity per trade.
- `STOP_LOSS_PCT` / `TAKE_PROFIT_PCT` — per-trade exit thresholds.
- `MAX_OPEN_POSITIONS`, `MAX_POSITION_PCT_OF_EQUITY` — caps concentration risk.
