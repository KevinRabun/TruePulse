"""
Event Aggregator Service

Aggregates current events from multiple news sources to identify
topics suitable for poll generation.

Implements multi-source aggregation using:
- NewsData.io (primary) - 79,451 sources, 206 countries, 89 languages
- NewsAPI.org (secondary) - 50,000+ sources, 50 countries, 24 months historical data
"""

import asyncio
import hashlib
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import httpx
import structlog
from pydantic import BaseModel, Field

from core.config import settings

logger = structlog.get_logger(__name__)


class NewsCategory(str, Enum):
    """Supported news categories aligned with APIs."""

    BUSINESS = "business"
    ENTERTAINMENT = "entertainment"
    ENVIRONMENT = "environment"
    FOOD = "food"
    HEALTH = "health"
    POLITICS = "politics"
    SCIENCE = "science"
    SPORTS = "sports"
    TECHNOLOGY = "technology"
    TOP = "top"
    WORLD = "world"


class NewsScope(str, Enum):
    """Geographic scope of news articles."""

    LOCAL = "local"  # City/regional news
    NATIONAL = "national"  # Country-wide news
    INTERNATIONAL = "international"  # Multi-country/global news


class NewsEvent(BaseModel):
    """A news event from aggregated sources."""

    id: str
    title: str
    summary: str
    source: str
    source_api: str = Field(description="Which API the event came from")
    url: str
    image_url: Optional[str] = None
    published_at: datetime
    category: str
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    keywords: list[str] = Field(default_factory=list)
    sentiment: Optional[str] = None  # positive, negative, neutral
    country: Optional[str] = None
    language: str = "en"
    scope: NewsScope = Field(default=NewsScope.NATIONAL, description="Geographic scope of the news")


class NewsDataClient:
    """
    Client for NewsData.io API.

    Free tier: 500 calls/month, max 10 articles per call
    https://newsdata.io/documentation
    """

    BASE_URL = "https://newsdata.io/api/1"

    def __init__(self, api_key: str, http_client: httpx.AsyncClient):
        self.api_key = api_key
        self.http_client = http_client

    async def fetch_news(
        self,
        categories: list[str] | None = None,
        keywords: str | None = None,
        country: str | None = "us",
        language: str = "en",
        size: int = 10,
    ) -> list[NewsEvent]:
        """Fetch news from NewsData.io."""
        params: dict[str, str | int] = {
            "apikey": self.api_key,
            "language": language,
            "size": min(size, 10),  # Max 10 per call on free tier
        }

        if categories:
            # NewsData uses comma-separated categories
            params["category"] = ",".join(categories[:5])  # Max 5 categories

        if keywords:
            params["q"] = keywords

        # Only add country filter if specified (None = global news)
        if country:
            params["country"] = country

        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/latest",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                logger.warning(f"NewsData API error: {data.get('results', {}).get('message', 'Unknown error')}")
                return []

            events = []
            for article in data.get("results", []):
                # Generate unique ID from title and source
                event_id = hashlib.md5(
                    f"{article.get('title', '')}-{article.get('source_id', '')}".encode()
                ).hexdigest()[:16]

                # Parse publication date
                pub_date = article.get("pubDate")
                if pub_date:
                    try:
                        published_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except ValueError:
                        published_at = datetime.now(timezone.utc)
                else:
                    published_at = datetime.now(timezone.utc)

                events.append(
                    NewsEvent(
                        id=f"nd-{event_id}",
                        title=article.get("title", ""),
                        summary=article.get("description") or article.get("content", "")[:500],
                        source=article.get("source_name") or article.get("source_id", "Unknown"),
                        source_api="newsdata",
                        url=article.get("link", ""),
                        image_url=article.get("image_url"),
                        published_at=published_at,
                        category=article.get("category", ["general"])[0] if article.get("category") else "general",
                        keywords=article.get("keywords", []) or [],
                        country=article.get("country", [None])[0] if article.get("country") else None,
                        language=article.get("language", "en"),
                        relevance_score=0.7,  # Default score for NewsData
                    )
                )

            logger.info(f"NewsData.io returned {len(events)} articles")
            return events

        except httpx.HTTPStatusError as e:
            logger.error(f"NewsData API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"NewsData API error: {e}")
            return []


class NewsAPIClient:
    """
    Client for NewsAPI.org.

    Free tier: 100 calls/day, max 100 articles per call
    Features: 50,000+ sources, 24 months historical data, 14 languages
    https://newsapi.org/docs
    """

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: str, http_client: httpx.AsyncClient):
        self.api_key = api_key
        self.http_client = http_client

    async def fetch_news(
        self,
        categories: list[str] | None = None,
        keywords: str | None = None,
        country: str | None = "us",
        language: str = "en",
        page_size: int = 20,
    ) -> list[NewsEvent]:
        """Fetch news from NewsAPI.org."""
        headers = {"X-Api-Key": self.api_key}

        # Use /everything for keyword search or global news, /top-headlines for country-specific
        params: dict[str, str | int]
        if keywords or not country:
            # Use /everything endpoint for keyword-based or global searches
            endpoint = f"{self.BASE_URL}/everything"
            params = {
                "language": language,
                "pageSize": min(page_size, 100),
                "sortBy": "relevancy",
            }
            if keywords:
                params["q"] = keywords
            else:
                # Default query for global news
                params["q"] = "world OR international OR economy OR politics"
                params["sortBy"] = "publishedAt"
        else:
            # Use /top-headlines for country-specific news
            endpoint = f"{self.BASE_URL}/top-headlines"
            params = {
                "country": country,
                "pageSize": min(page_size, 100),
            }
            if categories:
                # NewsAPI only supports one category at a time for top-headlines
                params["category"] = categories[0]

        try:
            response = await self.http_client.get(
                endpoint,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                logger.warning(f"NewsAPI.org error: {data.get('message', 'Unknown error')}")
                return []

            events = []
            for article in data.get("articles", []):
                # Skip removed articles
                if article.get("title") == "[Removed]":
                    continue

                # Generate unique ID
                source_name = article.get("source", {}).get("name", "Unknown")
                event_id = hashlib.md5(f"{article.get('title', '')}-{source_name}".encode()).hexdigest()[:16]

                # Parse publication date
                pub_date = article.get("publishedAt")
                if pub_date:
                    try:
                        published_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except ValueError:
                        published_at = datetime.now(timezone.utc)
                else:
                    published_at = datetime.now(timezone.utc)

                # Infer category from the request or content
                category = categories[0] if categories else self._infer_category(article)

                events.append(
                    NewsEvent(
                        id=f"na-{event_id}",
                        title=article.get("title", ""),
                        summary=article.get("description") or article.get("content", "")[:500] or "",
                        source=source_name,
                        source_api="newsapi",
                        url=article.get("url", ""),
                        image_url=article.get("urlToImage"),
                        published_at=published_at,
                        category=category,
                        keywords=[],  # NewsAPI doesn't provide keywords
                        country=country,
                        language=language,
                        relevance_score=0.72,  # Default score for NewsAPI
                    )
                )

            logger.info(f"NewsAPI.org returned {len(events)} articles")
            return events

        except httpx.HTTPStatusError as e:
            logger.error(f"NewsAPI.org HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"NewsAPI.org error: {e}")
            return []

    def _infer_category(self, article: dict) -> str:
        """Infer category from article content."""
        title = (article.get("title") or "").lower()
        description = (article.get("description") or "").lower()
        content = f"{title} {description}"

        category_keywords = {
            "politics": [
                "election",
                "president",
                "congress",
                "senate",
                "government",
                "political",
            ],
            "technology": ["tech", "ai", "software", "google", "apple", "microsoft"],
            "business": ["stock", "market", "economy", "ceo", "company", "trade"],
            "sports": ["game", "team", "player", "championship", "nba", "nfl"],
            "health": ["health", "medical", "doctor", "hospital", "disease"],
            "science": ["research", "study", "scientist", "discovery", "space"],
            "entertainment": ["movie", "music", "celebrity", "hollywood"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in content for kw in keywords):
                return category

        return "general"


def classify_news_scope(title: str, summary: str, keywords: list[str]) -> NewsScope:
    """
    Classify the geographic scope of a news article.

    Returns:
        NewsScope indicating local, national, or international reach
    """
    content = f"{title} {summary}".lower()
    keyword_str = " ".join(keywords).lower() if keywords else ""

    # International indicators - stories with global impact
    international_indicators = [
        # Global organizations and summits
        "united nations", "un ", "nato", "who ", "world health",
        "imf", "world bank", "g7", "g20", "opec", "european union", "eu ",
        # International events and issues
        "global", "worldwide", "international", "world leaders",
        "climate summit", "cop28", "cop29", "davos",
        "trade war", "sanctions", "tariff", "embargo",
        # Major world regions/conflicts
        "ukraine", "russia", "china", "middle east", "gaza", "israel",
        "taiwan", "north korea", "iran", "syria",
        # International business/tech
        "multinational", "global economy", "world market",
        "spacex", "nasa", "esa", "space station",
        # Pandemic/global health
        "pandemic", "outbreak", "vaccine rollout",
    ]

    # National indicators - country-wide significance
    national_indicators = [
        # Federal government and politics
        "president", "congress", "senate", "supreme court",
        "federal", "national", "white house", "capitol",
        "election", "primary", "ballot", "vote", "campaign",
        "legislation", "bill passed", "executive order",
        # National issues
        "nationwide", "across the country", "americans",
        "national security", "federal reserve", "fed rate",
        "inflation", "recession", "unemployment rate",
        "immigration", "border", "healthcare reform",
        # Major companies with national impact
        "fortune 500", "wall street", "dow jones", "nasdaq", "s&p",
        "big tech", "major airlines", "automakers",
        # National events
        "super bowl", "march madness", "thanksgiving",
        "memorial day", "labor day", "independence day",
    ]

    # Local/niche indicators - stories to filter out
    local_indicators = [
        # Local government
        "city council", "mayor", "county", "township", "alderman",
        "school board", "sheriff", "district attorney",
        "local police", "fire department",
        # Regional/local events
        "high school", "local business", "neighborhood",
        "downtown", "suburb", "community center",
        "local restaurant", "small town", "regional",
        # Traffic/weather (unless severe)
        "traffic accident", "car crash", "road closure",
        "local weather", "forecast",
        # Crime (unless major)
        "robbery", "burglary", "theft", "break-in",
        "drug arrest", "dui",
        # Niche financial news (individual company earnings, not market-wide)
        "eps estimate", "earnings estimate", "quarterly earnings",
        "fy2024", "fy2025", "fy2026", "fy2027",
        "price target", "analyst rating", "buy rating", "sell rating",
        "stock upgrade", "stock downgrade",
    ]

    # Check for international scope first (highest priority)
    if any(indicator in content or indicator in keyword_str for indicator in international_indicators):
        return NewsScope.INTERNATIONAL

    # Check for local/niche scope (filter out)
    local_count = sum(1 for indicator in local_indicators if indicator in content or indicator in keyword_str)
    if local_count >= 1:  # Changed from 2 to 1 for niche financial news
        return NewsScope.LOCAL

    # Check for national scope
    if any(indicator in content or indicator in keyword_str for indicator in national_indicators):
        return NewsScope.NATIONAL

    # Default to national if uncertain
    return NewsScope.NATIONAL


def calculate_relevance_boost(event: "NewsEvent") -> float:
    """
    Calculate a relevance score boost based on news scope and other factors.

    Returns:
        A multiplier (0.5 to 1.5) to apply to the base relevance score
    """
    boost = 1.0

    # Scope-based boost
    if event.scope == NewsScope.INTERNATIONAL:
        boost *= 1.3  # International news gets 30% boost
    elif event.scope == NewsScope.NATIONAL:
        boost *= 1.1  # National news gets 10% boost
    else:  # LOCAL
        boost *= 0.6  # Local news gets penalized

    # Category-based boost for topics with broader appeal
    high_interest_categories = {"politics", "technology", "world", "health", "science"}
    if event.category in high_interest_categories:
        boost *= 1.1

    # Major source boost (well-known outlets tend to cover bigger stories)
    major_sources = [
        "reuters", "associated press", "ap news", "bbc", "cnn",
        "new york times", "washington post", "wall street journal",
        "the guardian", "npr", "pbs", "abc news", "nbc news", "cbs news",
        "fox news", "bloomberg", "cnbc", "al jazeera", "france24",
    ]
    source_lower = event.source.lower()
    if any(src in source_lower for src in major_sources):
        boost *= 1.15

    return min(max(boost, 0.5), 1.5)  # Clamp between 0.5 and 1.5


class EventAggregator:
    """
    Aggregates current events from multiple news sources.

    Implements multiple source aggregation to ensure diverse
    perspectives and reduce bias in event selection.

    Sources:
    - NewsData.io: 79,451+ sources, 206 countries, historical data
    - NewsAPI.org: 50,000+ sources, 50 countries, 24 months history
    """

    def __init__(self) -> None:
        self.http_client: Optional[httpx.AsyncClient] = None
        self.newsdata_client: Optional[NewsDataClient] = None
        self.newsapi_client: Optional[NewsAPIClient] = None

    async def __aenter__(self) -> "EventAggregator":
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Initialize available clients
        if settings.NEWSDATA_API_KEY:
            self.newsdata_client = NewsDataClient(settings.NEWSDATA_API_KEY, self.http_client)
            logger.info("NewsData.io client initialized")

        if settings.NEWSAPI_ORG_API_KEY:
            self.newsapi_client = NewsAPIClient(settings.NEWSAPI_ORG_API_KEY, self.http_client)
            logger.info("NewsAPI.org client initialized")

        if not self.newsdata_client and not self.newsapi_client:
            logger.warning("No news API keys configured - using mock data")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.http_client:
            await self.http_client.aclose()

    async def fetch_trending_events(
        self,
        categories: list[str] | None = None,
        keywords: str | None = None,
        limit: int = 50,
        min_scope: NewsScope = NewsScope.NATIONAL,
    ) -> list[NewsEvent]:
        """
        Fetch trending events from multiple news sources with global reach.

        Sources are weighted to ensure political balance, diverse perspectives,
        and national/international relevance.

        Args:
            categories: Filter by news categories (politics, tech, etc.)
            keywords: Search keywords
            limit: Maximum number of events to return
            min_scope: Minimum geographic scope (filters out local news by default)

        Returns:
            List of NewsEvent objects from multiple sources, prioritized by relevance
        """
        logger.info(f"Fetching trending events, categories={categories}, keywords={keywords}, limit={limit}")

        all_events: list[NewsEvent] = []
        fetch_tasks = []

        # Count available clients
        num_clients = sum(
            [
                self.newsdata_client is not None,
                self.newsapi_client is not None,
            ]
        )

        # Calculate articles per source - fetch more to allow filtering
        articles_per_source = max((limit * 2) // max(num_clients, 1), 20)

        # Fetch from NewsData.io - use no country filter to get global news
        if self.newsdata_client:
            # First fetch: world/top news without country filter
            fetch_tasks.append(
                self.newsdata_client.fetch_news(
                    categories=categories or ["world", "politics", "business"],
                    keywords=keywords,
                    country=None,  # No country filter = global news
                    size=min(articles_per_source, 10),  # API limit
                )
            )

        # Fetch from NewsAPI.org - mix of US and global sources
        if self.newsapi_client:
            # Fetch from top-headlines (US for major domestic news)
            fetch_tasks.append(
                self.newsapi_client.fetch_news(
                    categories=categories,
                    keywords=keywords,
                    country="us",  # US national news
                    page_size=min(articles_per_source // 2, 50),
                )
            )
            # Fetch from /everything endpoint (global, keyword-based)
            if not keywords:
                # Use broad keywords to get internationally relevant news
                fetch_tasks.append(
                    self.newsapi_client.fetch_news(
                        categories=None,
                        keywords="world OR international OR global OR economy",
                        country=None,
                        page_size=min(articles_per_source // 2, 50),
                    )
                )

        # Execute all fetches concurrently
        if fetch_tasks:
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error fetching news: {result}")
                elif isinstance(result, list):
                    all_events.extend(result)

        # If no API keys configured, return mock data
        if not all_events and not fetch_tasks:
            all_events = self._get_mock_events()

        # Classify scope and apply relevance boost for each event
        for event in all_events:
            event.scope = classify_news_scope(event.title, event.summary, event.keywords)
            boost = calculate_relevance_boost(event)
            event.relevance_score = min(event.relevance_score * boost, 1.0)

        # Filter out local news (unless explicitly requested)
        scope_priority = {
            NewsScope.INTERNATIONAL: 3,
            NewsScope.NATIONAL: 2,
            NewsScope.LOCAL: 1,
        }
        min_scope_priority = scope_priority.get(min_scope, 2)

        filtered_events = [
            event for event in all_events
            if scope_priority.get(event.scope, 1) >= min_scope_priority
        ]

        logger.info(
            f"Scope filtering: {len(all_events)} total -> {len(filtered_events)} "
            f"(min_scope={min_scope.value})"
        )

        # Deduplicate and sort by relevance
        unique_events = await self.deduplicate_events(filtered_events)
        unique_events.sort(key=lambda e: e.relevance_score, reverse=True)

        logger.info(f"Aggregated {len(unique_events)} unique events from {len(fetch_tasks)} sources")
        return unique_events[:limit]

    async def fetch_by_topic(
        self,
        topic: str,
        limit: int = 20,
    ) -> list[NewsEvent]:
        """
        Fetch events related to a specific topic.

        Useful for getting context around a poll question.
        """
        return await self.fetch_trending_events(
            keywords=topic,
            limit=limit,
        )

    async def analyze_event_balance(
        self,
        events: list[NewsEvent],
    ) -> dict:
        """
        Analyze events for political/perspective balance.

        Ensures poll questions aren't biased toward any
        particular viewpoint.
        """
        if not events:
            return {
                "total_events": 0,
                "category_distribution": {},
                "source_distribution": {},
                "sentiment_distribution": {},
                "balance_score": 0.0,
            }

        # Category distribution
        category_counts: dict[str, int] = {}
        for event in events:
            category_counts[event.category] = category_counts.get(event.category, 0) + 1

        # Source API distribution
        source_api_counts: dict[str, int] = {}
        for event in events:
            source_api_counts[event.source_api] = source_api_counts.get(event.source_api, 0) + 1

        # Source (publication) distribution
        source_counts: dict[str, int] = {}
        for event in events:
            source_counts[event.source] = source_counts.get(event.source, 0) + 1

        # Sentiment distribution
        sentiment_counts: dict[str, int] = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "unknown": 0,
        }
        for event in events:
            sentiment_key = event.sentiment if event.sentiment else "unknown"
            sentiment_counts[sentiment_key] = sentiment_counts.get(sentiment_key, 0) + 1

        # Calculate balance score (0-1)
        # Higher score means more balanced across sources
        total = len(events)

        # Source diversity score (penalize if one source dominates)
        max_source_pct = max(source_counts.values()) / total if source_counts else 1.0
        source_diversity = 1.0 - max_source_pct

        # Sentiment balance (ideal is roughly equal positive/negative/neutral)
        sentiment_values = [
            sentiment_counts["positive"],
            sentiment_counts["negative"],
            sentiment_counts["neutral"],
        ]
        if sum(sentiment_values) > 0:
            sentiment_std = self._calculate_std(sentiment_values)
            max_sentiment_std = total / 3  # Max std would be if all in one category
            sentiment_balance = 1.0 - (sentiment_std / max_sentiment_std) if max_sentiment_std > 0 else 0.5
        else:
            sentiment_balance = 0.5

        # API diversity (using multiple APIs is good)
        api_diversity = len(source_api_counts) / 3.0  # Max 3 APIs currently

        balance_score = source_diversity * 0.4 + sentiment_balance * 0.4 + api_diversity * 0.2

        return {
            "total_events": total,
            "category_distribution": category_counts,
            "source_distribution": dict(list(source_counts.items())[:10]),  # Top 10 sources
            "source_api_distribution": source_api_counts,
            "sentiment_distribution": sentiment_counts,
            "balance_score": round(balance_score, 3),
        }

    def _calculate_std(self, values: list[int]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance**0.5

    async def deduplicate_events(
        self,
        events: list[NewsEvent],
        similarity_threshold: float = 0.8,
    ) -> list[NewsEvent]:
        """
        Remove duplicate events covering the same story.

        Uses title similarity to identify duplicates
        from different sources.
        """
        if not events:
            return []

        seen_titles: dict[str, NewsEvent] = {}
        unique_events: list[NewsEvent] = []

        for event in events:
            # Normalize title for comparison
            normalized_title = self._normalize_text(event.title)

            # Check for similar titles
            is_duplicate = False
            for seen_title, seen_event in list(seen_titles.items()):
                similarity = self._calculate_title_similarity(normalized_title, seen_title)
                if similarity >= similarity_threshold:
                    # Keep the one with higher relevance score
                    if event.relevance_score > seen_event.relevance_score:
                        # Replace with higher-scored event
                        unique_events.remove(seen_event)
                        unique_events.append(event)
                        seen_titles[normalized_title] = event
                        del seen_titles[seen_title]
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_titles[normalized_title] = event
                unique_events.append(event)

        return unique_events

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase, remove punctuation, extra spaces
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate Jaccard similarity between two titles."""
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    async def get_event_context(
        self,
        event: NewsEvent,
    ) -> dict:
        """
        Fetch additional context for an event.

        Gathers multiple perspectives to ensure unbiased
        poll question generation.
        """
        # Fetch related articles using the event's keywords
        related_events = await self.fetch_by_topic(
            topic=event.title,
            limit=5,
        )

        # Filter out the original event
        related_events = [e for e in related_events if e.id != event.id]

        # Analyze perspectives
        perspectives = []
        for related in related_events:
            if related.sentiment:
                perspectives.append(
                    {
                        "source": related.source,
                        "sentiment": related.sentiment,
                        "title": related.title,
                    }
                )

        return {
            "event_id": event.id,
            "related_articles": [
                {
                    "title": e.title,
                    "source": e.source,
                    "url": e.url,
                    "sentiment": e.sentiment,
                }
                for e in related_events[:5]
            ],
            "diverse_perspectives": perspectives,
            "keywords": event.keywords,
            "fact_checks": await self._fetch_fact_checks(event),
        }

    async def _fetch_fact_checks(
        self,
        event: NewsEvent,
    ) -> list[dict]:
        """
        Fetch fact-check information for an event.

        Uses Google Fact Check Tools API to find relevant fact checks
        for claims related to the event.

        Note: Requires GOOGLE_FACTCHECK_API_KEY in settings.
        Free tier: 10,000 queries/day
        https://developers.google.com/fact-check/tools/api
        """
        api_key = getattr(settings, "GOOGLE_FACTCHECK_API_KEY", None)

        if not api_key:
            # Return empty if API not configured
            return []

        try:
            # Build search query from event keywords
            query = " ".join(event.keywords[:5]) if event.keywords else event.title

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://factchecktools.googleapis.com/v1alpha1/claims:search",
                    params={
                        "key": api_key,
                        "query": query,
                        "languageCode": event.language or "en",
                        "pageSize": 5,
                    },
                    timeout=10.0,
                )

                if response.status_code != 200:
                    logger.warning(f"Fact check API error: status={response.status_code}, query='{query[:50]}'")
                    return []

                data = response.json()
                claims = data.get("claims", [])

                fact_checks = []
                for claim in claims:
                    # Extract claim review data
                    reviews = claim.get("claimReview", [])
                    if reviews:
                        review = reviews[0]  # Take first review
                        fact_checks.append(
                            {
                                "claim_text": claim.get("text", ""),
                                "claimant": claim.get("claimant", "Unknown"),
                                "claim_date": claim.get("claimDate"),
                                "rating": review.get("textualRating", ""),
                                "publisher": review.get("publisher", {}).get("name", ""),
                                "url": review.get("url", ""),
                                "title": review.get("title", ""),
                            }
                        )

                logger.info(f"Fetched {len(fact_checks)} fact checks for event {event.id}")

                return fact_checks

        except Exception as e:
            logger.error(f"Fact check fetch failed for event {event.id}: {e}")
            return []

    def _get_mock_events(self) -> list[NewsEvent]:
        """Return mock events for development/testing with diverse topics."""
        import random

        # Large pool of mock events across categories
        all_mock_events = [
            # Environment
            NewsEvent(
                id="mock-env-1",
                title="Global Climate Summit Reaches New Agreement",
                summary="World leaders at the climate summit have reached a new agreement on emissions targets, with commitments to reduce carbon output by 50% by 2030.",
                source="Reuters",
                source_api="mock",
                url="https://example.com/climate-summit",
                published_at=datetime.now(timezone.utc) - timedelta(hours=2),
                category="environment",
                relevance_score=0.95,
                keywords=["climate", "summit", "emissions", "agreement", "carbon"],
                sentiment="positive",
            ),
            NewsEvent(
                id="mock-env-2",
                title="Cities Announce Major Green Infrastructure Investment",
                summary="A coalition of major cities unveiled plans to invest billions in green infrastructure, including urban forests and sustainable transportation.",
                source="Environmental News",
                source_api="mock",
                url="https://example.com/green-infrastructure",
                published_at=datetime.now(timezone.utc) - timedelta(hours=3),
                category="environment",
                relevance_score=0.88,
                keywords=["cities", "green", "infrastructure", "sustainability"],
                sentiment="positive",
            ),
            NewsEvent(
                id="mock-env-3",
                title="Renewable Energy Adoption Accelerates Globally",
                summary="New report shows solar and wind power installations hit record highs as costs continue to decline.",
                source="Energy Monitor",
                source_api="mock",
                url="https://example.com/renewable-energy",
                published_at=datetime.now(timezone.utc) - timedelta(hours=5),
                category="environment",
                relevance_score=0.85,
                keywords=["renewable", "energy", "solar", "wind", "clean"],
                sentiment="positive",
            ),
            # Technology
            NewsEvent(
                id="mock-tech-1",
                title="Tech Industry Faces New Regulation Proposals",
                summary="Lawmakers propose new regulations for tech companies regarding AI and data privacy, sparking debate about innovation vs. consumer protection.",
                source="Associated Press",
                source_api="mock",
                url="https://example.com/tech-regulation",
                published_at=datetime.now(timezone.utc) - timedelta(hours=4),
                category="technology",
                relevance_score=0.88,
                keywords=["technology", "regulation", "AI", "privacy", "congress"],
                sentiment="neutral",
            ),
            NewsEvent(
                id="mock-tech-2",
                title="AI Assistants Transform Workplace Productivity",
                summary="Companies report significant productivity gains from AI assistant adoption, but concerns about job displacement persist.",
                source="Tech Today",
                source_api="mock",
                url="https://example.com/ai-workplace",
                published_at=datetime.now(timezone.utc) - timedelta(hours=6),
                category="technology",
                relevance_score=0.84,
                keywords=["AI", "workplace", "productivity", "automation"],
                sentiment="neutral",
            ),
            NewsEvent(
                id="mock-tech-3",
                title="Social Media Platforms Update Content Moderation Policies",
                summary="Major social networks announce changes to how they handle misinformation and harmful content.",
                source="Digital Trends",
                source_api="mock",
                url="https://example.com/social-media-policies",
                published_at=datetime.now(timezone.utc) - timedelta(hours=7),
                category="technology",
                relevance_score=0.82,
                keywords=["social media", "moderation", "content", "policy"],
                sentiment="neutral",
            ),
            # Business
            NewsEvent(
                id="mock-biz-1",
                title="Economic Report Shows Mixed Signals for Job Market",
                summary="The latest employment report reveals a complex picture with strong hiring in some sectors offset by layoffs in others.",
                source="Bloomberg",
                source_api="mock",
                url="https://example.com/jobs-report",
                published_at=datetime.now(timezone.utc) - timedelta(hours=6),
                category="business",
                relevance_score=0.82,
                keywords=["economy", "jobs", "employment", "market", "labor"],
                sentiment="neutral",
            ),
            NewsEvent(
                id="mock-biz-2",
                title="Remote Work Debate Intensifies as Companies Set Policies",
                summary="Major corporations take different approaches to remote work, with some requiring office return and others embracing flexibility.",
                source="Business Week",
                source_api="mock",
                url="https://example.com/remote-work",
                published_at=datetime.now(timezone.utc) - timedelta(hours=8),
                category="business",
                relevance_score=0.80,
                keywords=["remote work", "office", "employees", "flexibility"],
                sentiment="neutral",
            ),
            NewsEvent(
                id="mock-biz-3",
                title="Small Business Owners Report Challenges with Rising Costs",
                summary="Survey reveals that inflation and supply chain issues remain top concerns for small business owners.",
                source="Small Biz Daily",
                source_api="mock",
                url="https://example.com/small-business",
                published_at=datetime.now(timezone.utc) - timedelta(hours=9),
                category="business",
                relevance_score=0.78,
                keywords=["small business", "costs", "inflation", "economy"],
                sentiment="negative",
            ),
            # Health
            NewsEvent(
                id="mock-health-1",
                title="Healthcare Costs Continue to Rise Amid Policy Debates",
                summary="New data shows healthcare spending increased again this year, intensifying debates over insurance reform and drug pricing.",
                source="NPR",
                source_api="mock",
                url="https://example.com/healthcare-costs",
                published_at=datetime.now(timezone.utc) - timedelta(hours=8),
                category="health",
                relevance_score=0.79,
                keywords=["healthcare", "costs", "insurance", "policy", "drugs"],
                sentiment="negative",
            ),
            NewsEvent(
                id="mock-health-2",
                title="Mental Health Services Expand Amid Growing Demand",
                summary="Healthcare providers report increased investment in mental health programs as demand surges.",
                source="Health News",
                source_api="mock",
                url="https://example.com/mental-health",
                published_at=datetime.now(timezone.utc) - timedelta(hours=10),
                category="health",
                relevance_score=0.77,
                keywords=["mental health", "healthcare", "services", "wellness"],
                sentiment="positive",
            ),
            NewsEvent(
                id="mock-health-3",
                title="New Study Examines Work-Life Balance Impact on Health",
                summary="Research links poor work-life balance to increased health risks, prompting calls for workplace policy changes.",
                source="Medical Journal",
                source_api="mock",
                url="https://example.com/work-life-health",
                published_at=datetime.now(timezone.utc) - timedelta(hours=11),
                category="health",
                relevance_score=0.75,
                keywords=["work-life balance", "health", "stress", "workplace"],
                sentiment="neutral",
            ),
            # Science
            NewsEvent(
                id="mock-sci-1",
                title="Space Agency Announces New Mars Mission Timeline",
                summary="The space agency unveiled an ambitious new timeline for human Mars exploration, targeting the first crewed mission by 2040.",
                source="Science Daily",
                source_api="mock",
                url="https://example.com/mars-mission",
                published_at=datetime.now(timezone.utc) - timedelta(hours=10),
                category="science",
                relevance_score=0.75,
                keywords=["space", "mars", "nasa", "exploration", "mission"],
                sentiment="positive",
            ),
            NewsEvent(
                id="mock-sci-2",
                title="Breakthrough in Clean Energy Research Announced",
                summary="Scientists report significant progress on fusion energy technology that could revolutionize power generation.",
                source="Science Today",
                source_api="mock",
                url="https://example.com/fusion-energy",
                published_at=datetime.now(timezone.utc) - timedelta(hours=12),
                category="science",
                relevance_score=0.83,
                keywords=["science", "fusion", "energy", "research", "breakthrough"],
                sentiment="positive",
            ),
            # Politics
            NewsEvent(
                id="mock-pol-1",
                title="Lawmakers Debate Infrastructure Spending Priorities",
                summary="Congress considers new infrastructure bill with competing visions for transportation and broadband investment.",
                source="Political Wire",
                source_api="mock",
                url="https://example.com/infrastructure-debate",
                published_at=datetime.now(timezone.utc) - timedelta(hours=4),
                category="politics",
                relevance_score=0.87,
                keywords=["infrastructure", "congress", "spending", "transportation"],
                sentiment="neutral",
            ),
            NewsEvent(
                id="mock-pol-2",
                title="Voters Weigh In on Local Election Issues",
                summary="Local elections draw attention to community issues including public safety, education, and housing.",
                source="Civic News",
                source_api="mock",
                url="https://example.com/local-elections",
                published_at=datetime.now(timezone.utc) - timedelta(hours=6),
                category="politics",
                relevance_score=0.81,
                keywords=["elections", "local", "voting", "community"],
                sentiment="neutral",
            ),
            NewsEvent(
                id="mock-pol-3",
                title="Bipartisan Group Proposes Compromise on Key Legislation",
                summary="A bipartisan coalition of lawmakers presents a compromise bill aimed at breaking legislative gridlock.",
                source="Capitol Report",
                source_api="mock",
                url="https://example.com/bipartisan-compromise",
                published_at=datetime.now(timezone.utc) - timedelta(hours=8),
                category="politics",
                relevance_score=0.79,
                keywords=["bipartisan", "compromise", "legislation", "congress"],
                sentiment="positive",
            ),
            # World
            NewsEvent(
                id="mock-world-1",
                title="International Trade Agreement Negotiations Continue",
                summary="Countries engage in talks over trade terms that could reshape global commerce patterns.",
                source="World Affairs",
                source_api="mock",
                url="https://example.com/trade-negotiations",
                published_at=datetime.now(timezone.utc) - timedelta(hours=5),
                category="world",
                relevance_score=0.84,
                keywords=["trade", "international", "negotiations", "commerce"],
                sentiment="neutral",
            ),
            NewsEvent(
                id="mock-world-2",
                title="Global Health Organizations Coordinate Response Efforts",
                summary="International health bodies work together on preparedness strategies for future health challenges.",
                source="Global News",
                source_api="mock",
                url="https://example.com/global-health",
                published_at=datetime.now(timezone.utc) - timedelta(hours=7),
                category="world",
                relevance_score=0.80,
                keywords=["global", "health", "international", "cooperation"],
                sentiment="positive",
            ),
            # Entertainment
            NewsEvent(
                id="mock-ent-1",
                title="Streaming Services Competition Intensifies",
                summary="Major streaming platforms announce new content strategies as competition for subscribers heats up.",
                source="Entertainment Weekly",
                source_api="mock",
                url="https://example.com/streaming-competition",
                published_at=datetime.now(timezone.utc) - timedelta(hours=9),
                category="entertainment",
                relevance_score=0.76,
                keywords=["streaming", "entertainment", "media", "content"],
                sentiment="neutral",
            ),
            # Sports
            NewsEvent(
                id="mock-sports-1",
                title="Athletes Speak Out on Sports Governance Issues",
                summary="Professional athletes call for reforms in how sports leagues are managed and how players are represented.",
                source="Sports Network",
                source_api="mock",
                url="https://example.com/sports-governance",
                published_at=datetime.now(timezone.utc) - timedelta(hours=11),
                category="sports",
                relevance_score=0.74,
                keywords=["sports", "athletes", "governance", "reform"],
                sentiment="neutral",
            ),
        ]

        # Shuffle and return a subset to ensure variety
        random.shuffle(all_mock_events)
        return all_mock_events[:10]
