from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/supply_chain_risk")
    database_url_sync: str = os.getenv("DATABASE_URL_SYNC", "postgresql://user:password@localhost:5432/supply_chain_risk")

    firebase_credentials_path: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-service-account.json")

    news_api_key: str = os.getenv("NEWS_API_KEY", "")
    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")

    ai_model_api_key: str = os.getenv("AI_MODEL_API_KEY", "")
    ai_model_url: str = os.getenv(
        "AI_MODEL_URL",
        "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
    )

    secret_key: str = os.getenv("SECRET_KEY", "change-me-to-a-random-secret")
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))


settings = Settings()
