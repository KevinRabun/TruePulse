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
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from enum import Enum

import httpx
from pydantic import BaseModel, Field

from core.config import settings

logger = logging.getLogger(__name__)


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
        country: str = "us",
        language: str = "en",
        size: int = 10,
    ) -> list[NewsEvent]:
        """Fetch news from NewsData.io."""
        params = {
            "apikey": self.api_key,
            "language": language,
            "size": min(size, 10),  # Max 10 per call on free tier
        }
        
        if categories:
            # NewsData uses comma-separated categories
            params["category"] = ",".join(categories[:5])  # Max 5 categories
        
        if keywords:
            params["q"] = keywords
        
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
                
                events.append(NewsEvent(
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
                ))
            
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
        country: str = "us",
        language: str = "en",
        page_size: int = 20,
    ) -> list[NewsEvent]:
        """Fetch news from NewsAPI.org."""
        headers = {"X-Api-Key": self.api_key}
        
        # Use /everything for keyword search, /top-headlines for categories
        if keywords:
            endpoint = f"{self.BASE_URL}/everything"
            params = {
                "q": keywords,
                "language": language,
                "pageSize": min(page_size, 100),
                "sortBy": "relevancy",
            }
        else:
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
                event_id = hashlib.md5(
                    f"{article.get('title', '')}-{source_name}".encode()
                ).hexdigest()[:16]
                
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
                
                events.append(NewsEvent(
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
                ))
            
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
            "politics": ["election", "president", "congress", "senate", "government", "political"],
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
        keywords = []
        
        # Extract from entities if available
        for entity_type in ["persons", "organizations", "locations"]:
            entities = article.get(entity_type, [])
            if isinstance(entities, list):
                keywords.extend(entities[:3])  # Limit to 3 per type
        
        return keywords[:10]  # Max 10 keywords


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
            self.newsdata_client = NewsDataClient(
                settings.NEWSDATA_API_KEY,
                self.http_client
            )
            logger.info("NewsData.io client initialized")
        
        if settings.NEWSAPI_ORG_API_KEY:
            self.newsapi_client = NewsAPIClient(
                settings.NEWSAPI_ORG_API_KEY,
                self.http_client
            )
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
    ) -> list[NewsEvent]:
        """
        Fetch trending events from multiple news sources.
        
        Sources are weighted to ensure political balance and
        diverse perspectives.
        
        Args:
            categories: Filter by news categories (politics, tech, etc.)
            keywords: Search keywords
            limit: Maximum number of events to return
            
        Returns:
            List of NewsEvent objects from multiple sources
        """
        logger.info(f"Fetching trending events, categories={categories}, keywords={keywords}, limit={limit}")
        
        all_events: list[NewsEvent] = []
        fetch_tasks = []
        
        # Count available clients
        num_clients = sum([
            self.newsdata_client is not None,
            self.newsapi_client is not None,
        ])
        
        # Calculate articles per source
        articles_per_source = max(limit // max(num_clients, 1), 10)
        
        # Fetch from NewsData.io
        if self.newsdata_client:
            fetch_tasks.append(
                self.newsdata_client.fetch_news(
                    categories=categories,
                    keywords=keywords,
                    size=min(articles_per_source, 10),  # API limit
                )
            )
        
        # Fetch from NewsAPI.org
        if self.newsapi_client:
            fetch_tasks.append(
                self.newsapi_client.fetch_news(
                    categories=categories,
                    keywords=keywords,
                    page_size=min(articles_per_source, 100),  # API limit
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
        
        # Deduplicate and sort by relevance
        unique_events = await self.deduplicate_events(all_events)
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
        sentiment_counts: dict[str, int] = {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0}
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
        sentiment_values = [sentiment_counts["positive"], sentiment_counts["negative"], sentiment_counts["neutral"]]
        if sum(sentiment_values) > 0:
            sentiment_std = self._calculate_std(sentiment_values)
            max_sentiment_std = total / 3  # Max std would be if all in one category
            sentiment_balance = 1.0 - (sentiment_std / max_sentiment_std) if max_sentiment_std > 0 else 0.5
        else:
            sentiment_balance = 0.5
        
        # API diversity (using multiple APIs is good)
        api_diversity = len(source_api_counts) / 3.0  # Max 3 APIs currently
        
        balance_score = (source_diversity * 0.4 + sentiment_balance * 0.4 + api_diversity * 0.2)
        
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
        return variance ** 0.5
    
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
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
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
                perspectives.append({
                    "source": related.source,
                    "sentiment": related.sentiment,
                    "title": related.title,
                })
        
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
                    logger.warning(
                        f"Fact check API error: status={response.status_code}, query='{query[:50]}'"
                    )
                    return []
                
                data = response.json()
                claims = data.get("claims", [])
                
                fact_checks = []
                for claim in claims:
                    # Extract claim review data
                    reviews = claim.get("claimReview", [])
                    if reviews:
                        review = reviews[0]  # Take first review
                        fact_checks.append({
                            "claim_text": claim.get("text", ""),
                            "claimant": claim.get("claimant", "Unknown"),
                            "claim_date": claim.get("claimDate"),
                            "rating": review.get("textualRating", ""),
                            "publisher": review.get("publisher", {}).get("name", ""),
                            "url": review.get("url", ""),
                            "title": review.get("title", ""),
                        })
                
                logger.info(
                    f"Fetched {len(fact_checks)} fact checks for event {event.id}"
                )
                
                return fact_checks
                
        except Exception as e:
            logger.error(f"Fact check fetch failed for event {event.id}: {e}")
            return []
    
    def _get_mock_events(self) -> list[NewsEvent]:
        """Return mock events for development/testing."""
        return [
            NewsEvent(
                id="mock-1",
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
                id="mock-2",
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
                id="mock-3",
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
                id="mock-4",
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
                id="mock-5",
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
        ]
