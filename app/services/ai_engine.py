import json
from typing import Any
from app.services.data_broker import data_broker
from app.core.config import settings

ANALYSIS_SCHEMA = {
    "risk_level": "string (low|medium|high|critical)",
    "overall_score": "float 0-100",
    "factors": [
        {
            "category": "string",
            "description": "string",
            "severity": "string (low|medium|high|critical)",
            "score": "float 0-100",
        }
    ],
    "advisory": "string",
    "recommended_actions": ["string"],
    "forecast_bias": "string (optimistic|neutral|pessimistic)",
}


async def analyze_risk(reference_object: dict) -> dict:
    """
    Pass the assembled reference object through the AI model using a strict schema.
    Falls back to rule-based scoring if the AI service is unavailable.
    """
    prompt = _build_prompt(reference_object)

    try:
        result = await data_broker.post(
            settings.ai_model_url,
            payload={"inputs": prompt, "parameters": {"max_new_tokens": 1024, "temperature": 0.3}},
            headers={"Authorization": f"Bearer {settings.ai_model_api_key}"},
        )
        parsed = _parse_ai_response(result)
        if parsed:
            return parsed
    except Exception:
        pass

    return _rule_based_fallback(reference_object)


def _build_prompt(ref: dict) -> str:
    return f"""<s>[INST] You are a supply chain risk analyst. Analyze the following delivery data and return a JSON risk assessment.

DELIVERY:
- Route: {ref.get('origin', 'Unknown')} → {ref.get('destination', 'Unknown')}
- Cargo: {ref.get('cargo_description', 'General goods')} (Value: ${ref.get('cargo_value', 0):,.2f})
- Departure: {ref.get('scheduled_departure', 'N/A')}
- Arrival: {ref.get('scheduled_arrival', 'N/A')}

WEATHER (Origin): {json.dumps(ref.get('origin_weather', {}), indent=2)}
WEATHER (Destination): {json.dumps(ref.get('dest_weather', {}), indent=2)}

NEWS ALERTS: {json.dumps(ref.get('news', {}), indent=2)}

ACTIVE RISK RULES: {json.dumps(ref.get('risk_rules', []), indent=2)}

Return ONLY valid JSON matching this schema:
{json.dumps(ANALYSIS_SCHEMA, indent=2)}
[/INST]"""


def _parse_ai_response(response: Any) -> Any:
    try:
        if isinstance(response, list) and response:
            text = response[0].get("generated_text", "")
        elif isinstance(response, dict):
            text = response.get("generated_text", "") or response.get("text", "")
        else:
            return None

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    return None


def _rule_based_fallback(ref: dict) -> dict:
    """Deterministic scoring when AI is unavailable."""
    weather_score = _score_weather(ref.get("origin_weather", {}), ref.get("dest_weather", {}))
    news_score = _score_news(ref.get("news", {}))
    geopolitical_score = _score_geopolitical(ref.get("news", {}))
    route_score = _score_route(ref)

    weights = {"weather": 0.30, "news": 0.25, "geopolitical": 0.25, "route": 0.20}
    overall = (
        weather_score * weights["weather"]
        + news_score * weights["news"]
        + geopolitical_score * weights["geopolitical"]
        + route_score * weights["route"]
    )

    risk_rules = ref.get("risk_rules", [])
    for rule in risk_rules:
        overall = _apply_rule(overall, rule, ref)

    overall = min(100, max(0, overall))

    if overall >= 75:
        level, advisory = "critical", "Immediate attention required. Consider rerouting or delaying shipment."
    elif overall >= 50:
        level, advisory = "high", "Significant risks identified. Review mitigation options before proceeding."
    elif overall >= 25:
        level, advisory = "medium", "Moderate risks present. Monitor conditions and have contingency plans ready."
    else:
        level, advisory = "low", "Conditions are favorable. Proceed with standard monitoring."

    factors = []
    for name, score in [("weather", weather_score), ("news", news_score), ("geopolitical", geopolitical_score), ("route", route_score)]:
        severity = "critical" if score >= 75 else "high" if score >= 50 else "medium" if score >= 25 else "low"
        factors.append({"category": name, "description": f"{name.title()} risk assessment", "severity": severity, "score": score})

    return {
        "risk_level": level,
        "overall_score": round(overall, 2),
        "factors": factors,
        "advisory": advisory,
        "recommended_actions": _generate_actions(level, factors),
        "forecast_bias": "neutral",
        "weather_score": weather_score,
        "news_score": news_score,
        "geopolitical_score": geopolitical_score,
        "route_score": route_score,
    }


def _score_weather(origin_wx: dict, dest_wx: dict) -> float:
    score = 0.0
    for wx in [origin_wx, dest_wx]:
        for alert in wx.get("alerts", []):
            sev = alert.get("severity", "low")
            score += {"critical": 40, "high": 25, "medium": 15, "low": 5}.get(sev, 5)
    return min(100, score)


def _score_news(news: dict) -> float:
    articles = news.get("articles", [])
    if not articles:
        return 0.0
    tagged_count = sum(1 for a in articles if a.get("relevance_tags"))
    return min(100, tagged_count * 15)


def _score_geopolitical(news: dict) -> float:
    geo_keywords = {"embargo", "sanction", "border closure", "conflict", "war", "coup", "unrest"}
    articles = news.get("articles", [])
    score = 0.0
    for a in articles:
        text = f"{a.get('title', '')} {a.get('description', '')}".lower()
        if any(kw in text for kw in geo_keywords):
            score += 20
    return min(100, score)


def _score_route(ref: dict) -> float:
    import math
    olat, olon = ref.get("origin_lat", 0), ref.get("origin_lon", 0)
    dlat, dlon = ref.get("dest_lat", 0), ref.get("dest_lon", 0)
    distance_km = _haversine(olat, olon, dlat, dlon)
    if distance_km > 5000:
        return 40
    elif distance_km > 2000:
        return 25
    elif distance_km > 500:
        return 15
    return 5


def _haversine(lat1, lon1, lat2, lon2) -> float:
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _apply_rule(score: float, rule: dict, ref: dict) -> float:
    condition = rule.get("condition", {})
    weight = rule.get("weight", 1.0)
    field = condition.get("field", "")
    operator = condition.get("operator", "")
    value = condition.get("value", 0)

    actual = ref.get(field)
    if actual is None:
        return score

    triggered = False
    if operator == "gt" and actual > value:
        triggered = True
    elif operator == "lt" and actual < value:
        triggered = True
    elif operator == "eq" and actual == value:
        triggered = True
    elif operator == "contains" and isinstance(actual, str) and value in actual:
        triggered = True

    if triggered:
        score += 10 * weight

    return score


def _generate_actions(level: str, factors: list) -> list[str]:
    actions = []
    if level in ("critical", "high"):
        actions.append("Alert dispatchers and supervisors immediately")
        actions.append("Evaluate alternative routes")
    for f in factors:
        if f["category"] == "weather" and f["score"] >= 50:
            actions.append("Monitor weather conditions hourly and prepare for delays")
        if f["category"] == "news" and f["score"] >= 50:
            actions.append("Review latest regional news for emerging disruptions")
        if f["category"] == "geopolitical" and f["score"] >= 50:
            actions.append("Consult compliance team on regulatory risks")
    if not actions:
        actions.append("Continue standard delivery monitoring")
    return actions
