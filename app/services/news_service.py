from app.services.data_broker import data_broker
from app.core.config import settings


NEWS_BASE_URL = "https://newsapi.org/v2"

SUPPLY_CHAIN_KEYWORDS = [
    "supply chain disruption",
    "port closure",
    "shipping delay",
    "trade embargo",
    "border closure",
    "strike logistics",
    "fuel shortage",
    "natural disaster",
    "infrastructure damage",
    "customs delay",
]


async def get_news_for_location(location_name: str) -> dict:
    """Fetch supply-chain-relevant news for a named location."""
    query = f"{location_name} ({' OR '.join(SUPPLY_CHAIN_KEYWORDS[:5])})"

    params = {
        "q": query,
        "sortBy": "relevancy",
        "pageSize": 10,
        "apiKey": settings.news_api_key,
        "language": "en",
    }

    raw = await data_broker.fetch(f"{NEWS_BASE_URL}/everything", params=params)
    articles = raw.get("articles", [])

    return {
        "location": location_name,
        "article_count": len(articles),
        "articles": [
            {
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "source": a.get("source", {}).get("name", ""),
                "published_at": a.get("publishedAt", ""),
                "url": a.get("url", ""),
                "relevance_tags": _tag_article(a),
            }
            for a in articles
        ],
    }


def _tag_article(article: dict) -> list[str]:
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    return [kw for kw in SUPPLY_CHAIN_KEYWORDS if kw in text]
