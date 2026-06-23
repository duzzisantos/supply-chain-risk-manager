"""
Orchestrator: assembles the reference object from delivery data, weather, news,
and risk rules, then passes it through the AI engine for analysis.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.delivery import Delivery
from app.models.risk_analysis import RiskAnalysis, RiskRule
from app.models.event_log import EventLog
from app.services.weather_service import get_weather_for_location
from app.services.news_service import get_news_for_location
from app.services.ai_engine import analyze_risk


async def run_analysis(delivery_id: UUID, db: AsyncSession) -> RiskAnalysis:
    delivery = await db.get(Delivery, delivery_id)
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} not found")

    origin_weather = await _safe_fetch(
        get_weather_for_location, delivery.origin_lat, delivery.origin_lon
    )
    dest_weather = await _safe_fetch(
        get_weather_for_location, delivery.dest_lat, delivery.dest_lon
    )

    origin_news = await _safe_fetch(get_news_for_location, delivery.origin)
    dest_news = await _safe_fetch(get_news_for_location, delivery.destination)
    combined_news = _merge_news(origin_news, dest_news)

    rules_result = await db.execute(select(RiskRule).where(RiskRule.is_active == "true"))
    active_rules = [
        {"name": r.name, "category": r.category, "condition": r.condition, "weight": r.weight}
        for r in rules_result.scalars().all()
    ]

    reference_object = {
        "origin": delivery.origin,
        "origin_lat": delivery.origin_lat,
        "origin_lon": delivery.origin_lon,
        "destination": delivery.destination,
        "dest_lat": delivery.dest_lat,
        "dest_lon": delivery.dest_lon,
        "cargo_description": delivery.cargo_description,
        "cargo_value": delivery.cargo_value,
        "scheduled_departure": str(delivery.scheduled_departure),
        "scheduled_arrival": str(delivery.scheduled_arrival),
        "origin_weather": origin_weather,
        "dest_weather": dest_weather,
        "news": combined_news,
        "risk_rules": active_rules,
    }

    analysis_result = await analyze_risk(reference_object)

    risk_analysis = RiskAnalysis(
        delivery_id=delivery_id,
        overall_score=analysis_result.get("overall_score", 0),
        weather_score=analysis_result.get("weather_score", 0),
        news_score=analysis_result.get("news_score", 0),
        geopolitical_score=analysis_result.get("geopolitical_score", 0),
        route_score=analysis_result.get("route_score", 0),
        advisory=analysis_result.get("advisory", ""),
        ai_summary=str(analysis_result.get("factors", [])),
        risk_factors=analysis_result,
        weather_data={"origin": origin_weather, "destination": dest_weather},
        news_data=combined_news,
    )
    db.add(risk_analysis)

    event = EventLog(
        delivery_id=delivery_id,
        event_type="risk_analysis_completed",
        description=f"Risk score: {risk_analysis.overall_score} ({analysis_result.get('risk_level', 'unknown')})",
        new_state={"overall_score": risk_analysis.overall_score, "risk_level": analysis_result.get("risk_level")},
    )
    db.add(event)

    await db.flush()
    return risk_analysis


async def _safe_fetch(func, *args):
    try:
        return await func(*args)
    except Exception:
        return {}


def _merge_news(origin_news: dict, dest_news: dict) -> dict:
    origin_articles = origin_news.get("articles", [])
    dest_articles = dest_news.get("articles", [])
    seen_titles = set()
    merged = []
    for article in origin_articles + dest_articles:
        title = article.get("title", "")
        if title not in seen_titles:
            seen_titles.add(title)
            merged.append(article)
    return {"article_count": len(merged), "articles": merged}
