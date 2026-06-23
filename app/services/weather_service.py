from app.services.data_broker import data_broker
from app.core.config import settings


WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


async def get_weather_for_location(lat: float, lon: float) -> dict:
    """Fetch current weather + 5-day forecast for a coordinate pair."""
    current = await data_broker.fetch(
        f"{WEATHER_BASE_URL}/weather",
        params={"lat": lat, "lon": lon, "appid": settings.weather_api_key, "units": "metric"},
    )

    forecast = await data_broker.fetch(
        f"{WEATHER_BASE_URL}/forecast",
        params={"lat": lat, "lon": lon, "appid": settings.weather_api_key, "units": "metric"},
    )

    return {
        "current": {
            "temp": current.get("main", {}).get("temp"),
            "humidity": current.get("main", {}).get("humidity"),
            "wind_speed": current.get("wind", {}).get("speed"),
            "description": current.get("weather", [{}])[0].get("description", ""),
            "visibility": current.get("visibility"),
        },
        "alerts": _extract_weather_risks(current),
        "forecast_summary": _summarize_forecast(forecast),
    }


def _extract_weather_risks(weather: dict) -> list[dict]:
    risks = []
    wind = weather.get("wind", {}).get("speed", 0)
    if wind > 20:
        risks.append({"type": "high_wind", "severity": "high", "detail": f"Wind speed {wind} m/s"})
    elif wind > 10:
        risks.append({"type": "moderate_wind", "severity": "medium", "detail": f"Wind speed {wind} m/s"})

    visibility = weather.get("visibility", 10000)
    if visibility < 1000:
        risks.append({"type": "low_visibility", "severity": "high", "detail": f"Visibility {visibility}m"})

    main_condition = weather.get("weather", [{}])[0].get("main", "").lower()
    severe = {"thunderstorm", "tornado", "hurricane", "snow", "blizzard"}
    if main_condition in severe:
        risks.append({"type": "severe_weather", "severity": "critical", "detail": main_condition})

    return risks


def _summarize_forecast(forecast: dict) -> list[dict]:
    entries = forecast.get("list", [])[:8]
    return [
        {
            "datetime": e.get("dt_txt"),
            "temp": e.get("main", {}).get("temp"),
            "description": e.get("weather", [{}])[0].get("description", ""),
            "wind_speed": e.get("wind", {}).get("speed"),
        }
        for e in entries
    ]
