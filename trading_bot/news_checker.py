"""
Fetches recent news for a symbol via Alpaca's News API and scores it with
VADER sentiment analysis. The bot uses this as a gate: it will not buy a
symbol unless recent news sentiment is not clearly negative.

Note on scope: this checks Alpaca's aggregated news feed (which pulls from
Benzinga, Business Wire, PR Newswire, GlobeNewswire, and other real financial
news sources). It is NOT literally "every news platform on the internet" --
no bot can guarantee that -- but it is a real, live financial-news source
rather than a placeholder.
"""

import logging
from datetime import datetime, timedelta, timezone

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger("trading_bot.news")

_analyzer = SentimentIntensityAnalyzer()


class NewsChecker:
    def __init__(self, news_client, lookback_hours: int, min_headlines: int, min_score: float):
        self.news_client = news_client
        self.lookback_hours = lookback_hours
        self.min_headlines = min_headlines
        self.min_score = min_score

    def get_recent_headlines(self, symbol: str):
        """Fetch recent news headlines for a symbol from Alpaca News API."""
        from alpaca.data.requests import NewsRequest

        start = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        try:
            req = NewsRequest(symbols=symbol, start=start, limit=50)
            news_set = self.news_client.get_news(req)
            articles = news_set.data.get("news", []) if hasattr(news_set, "data") else news_set.news
            headlines = [a.headline for a in articles if getattr(a, "headline", None)]
            return headlines
        except Exception as e:
            logger.error(f"[{symbol}] Failed to fetch news: {e}")
            return []

    def score_headlines(self, headlines):
        if not headlines:
            return 0.0
        scores = [_analyzer.polarity_scores(h)["compound"] for h in headlines]
        return sum(scores) / len(scores)

    def is_safe_to_buy(self, symbol: str):
        """
        Returns (allowed: bool, reason: str, avg_sentiment: float, headline_count: int)
        """
        headlines = self.get_recent_headlines(symbol)

        if len(headlines) < self.min_headlines:
            return False, "insufficient recent news to evaluate risk", 0.0, len(headlines)

        avg_score = self.score_headlines(headlines)

        if avg_score < self.min_score:
            return False, f"news sentiment too negative ({avg_score:.2f})", avg_score, len(headlines)

        return True, f"sentiment ok ({avg_score:.2f}) over {len(headlines)} headlines", avg_score, len(headlines)
