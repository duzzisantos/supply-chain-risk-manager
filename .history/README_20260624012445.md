# Supply Chain Risk Analyzer

AI-powered supply chain risk assessment API that aggregates weather, news, and geopolitical data to score delivery risk in real time.

## Architecture

```
    Authentication Required
    Service Query Properties Required
                │
  ┌─────────────▼──────────────┐        Caching       ┌───────────────────┐
  │      Backend Service       │ ────────────────────▶ │    Data Broker    │
  │        (FastAPI)           │      Rate Limit       │ (httpx + tenacity)│
  └─────────────┬──────────────┘                       └───────────────────┘
                │                                             │
     ┌──────────▼──────────┐                     ┌────────────▼────────────┐
     │                     │                     │    External APIs        │
     │     ┌───┐           │                     │  ┌─────────────────┐   │
     │     │DB │           │                     │  │  OpenWeatherMap  │   │
     │     └─┬─┘           │                     │  │  NewsAPI         │   │
     │       │             │                     │  │  HuggingFace AI  │   │
     │       ▼             │                     │  └─────────────────┘   │
     │ ┌───────────────┐   │                     └────────────────────────┘
     │ │ User Delivery  │   │
     │ │ Schedule       │   │
     │ │ Properties     │   │
     │ └───────┬────────┘   │
     │         │            │
     │         ▼            │
     │ ┌───────────────┐   │       ┌───────────────────────────────────┐
     │ │    Risk        │◀─┼───────│  Location-based news feed         │
     │ │    References  │   │       │  Location-based weather feed      │
     │ └───────┬────────┘   │       └───────────────────────────────────┘
     │         │            │
     │         ▼            │             ┌────────────┐
     │ ┌───────────────────┐│             │            │
     │ │ Reference object   ││◀────────── │ Risk Rules │
     │ │ passed through AI  ││  Inject    │            │
     │ │ model using strict ││  rules     └────────────┘
     │ │ schema             ││
     │ └───────┬────────────┘│
     │         │             │
     │         ▼             │
     │ ┌───────────────────┐ │    ┌────────────────────────────────┐
     │ │ Risk analysis      │ │    │ User delivery primary data     │
     │ │ result returned    │─┼──▶ │ returned                       │
     │ └───────┬────────────┘ │    ├────────────────────────────────┤
     │         │              │    │ Forecasts and biases returned  │
     │         ▼              │    ├────────────────────────────────┤
     │ ┌───────────────────┐  │    │ Risk score and advisory        │
     │ │   Save to DB      │  │    │ information returned           │
     │ │                   │  │    └────────────────────────────────┘
     │ │  • risk_analyses  │  │
     │ │    (Delivery ID   │  │     ─── Update Risk Analysis Result
     │ │     as FK)        │  │
     │ │  • event_logs     │  │     ─── Save Event Log to DB
     │ └───────────────────┘  │
     │                        │
     └────────────────────────┘
                │
                │  Event Listener Tracking Reference Changes
                ▼
     ┌────────────────────┐
     │  State Changes?    │──── Yes ───▶ Trigger Re-Analysis ──┐
     └────────────────────┘                                    │
                ▲                                              │
                └──────────────────────────────────────────────┘
```

## How It Works

1. A user creates a **delivery** with origin/destination coordinates, cargo details, and scheduled times.
2. Triggering `/api/v1/risk/analyze/{id}` kicks off the **Risk Analyzer**, which:
   - Fetches live weather from OpenWeatherMap for both origin and destination.
   - Pulls supply-chain-relevant news from NewsAPI (port closures, strikes, embargoes, etc.).
   - Assembles a reference object and sends it to a **Mistral-7B** model on HuggingFace for AI-generated analysis.
   - Falls back to a deterministic **rule-based scorer** if the AI service is unavailable.
3. Scores are stored as a `RiskAnalysis` record and an `EventLog` entry is created.
4. When a delivery is updated (route change, status change, rescheduling), the **Event Listener** detects significant changes and automatically triggers re-analysis.

## Tech Stack

| Layer              | Technology                                |
|--------------------|-------------------------------------------|
| Framework          | FastAPI 0.128                             |
| Server             | Uvicorn (ASGI)                            |
| Database           | PostgreSQL via asyncpg + SQLAlchemy 2.0   |
| Migrations         | Alembic                                   |
| Auth               | Firebase Admin SDK (ID token verification)|
| HTTP Client        | httpx with tenacity retry                 |
| AI Model           | Mistral-7B-Instruct via HuggingFace API   |
| Weather Data       | OpenWeatherMap (current + 5-day forecast) |
| News Data          | NewsAPI (relevancy-ranked articles)       |
| Validation         | Pydantic v2                               |

## Project Structure

```
supply-chain-risk/
├── run.py                      # Uvicorn entry point
├── requirements.txt
├── .env.example                # Required env vars template
├── alembic/                    # Database migration config
│   ├── alembic.ini
│   └── env.py
└── app/
    ├── main.py                 # FastAPI app, lifespan, middleware
    ├── core/
    │   ├── config.py           # Pydantic settings from env vars
    │   └── auth.py             # Firebase token verification
    ├── db/
    │   └── session.py          # Async engine, session factory
    ├── models/
    │   ├── delivery.py         # Delivery ORM model + status enum
    │   ├── risk_analysis.py    # RiskAnalysis + RiskRule models
    │   └── event_log.py        # EventLog model
    ├── schemas/
    │   ├── delivery.py         # Create, Update, Response schemas
    │   └── risk.py             # Analysis, Rule, Summary schemas
    ├── api/routes/
    │   ├── health.py           # GET /health
    │   ├── deliveries.py       # CRUD for deliveries
    │   ├── risk.py             # Trigger analysis, history, rules
    │   └── events.py           # Event log retrieval
    └── services/
        ├── risk_analyzer.py    # Orchestrates the full analysis pipeline
        ├── weather_service.py  # OpenWeatherMap integration
        ├── news_service.py     # NewsAPI integration
        ├── ai_engine.py        # HuggingFace model + rule-based fallback
        ├── data_broker.py      # Caching HTTP proxy with rate limiting
        └── event_listener.py   # Detects changes, triggers re-analysis
```

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL (or a hosted instance like Supabase)
- Firebase project (for auth tokens)

### Setup

```bash
# Clone and enter
git clone <repo-url> && cd supply-chain-risk

# Virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL, API keys, and Firebase credentials
```

### Environment Variables

| Variable                    | Description                                    |
|-----------------------------|------------------------------------------------|
| `DATABASE_URL`              | PostgreSQL connection string with `+asyncpg`   |
| `DATABASE_URL_SYNC`         | PostgreSQL connection string (for Alembic)     |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase service account JSON          |
| `NEWS_API_KEY`              | NewsAPI.org API key                            |
| `WEATHER_API_KEY`           | OpenWeatherMap API key                         |
| `AI_MODEL_API_KEY`          | HuggingFace API token                          |
| `AI_MODEL_URL`              | HuggingFace inference endpoint                 |
| `SECRET_KEY`                | App secret for signing                         |
| `RATE_LIMIT_PER_MINUTE`     | Max external API calls per minute (default 60) |

### Run

```bash
python run.py
# Server starts at http://127.0.0.1:5000
# Swagger docs at http://127.0.0.1:5000/docs
```

Tables are created automatically on first startup via `Base.metadata.create_all`.

## API Endpoints

### Health
| Method | Path       | Description        |
|--------|------------|--------------------|
| GET    | `/health`  | Service health check |

### Deliveries
| Method | Path                          | Description               |
|--------|-------------------------------|---------------------------|
| POST   | `/api/v1/deliveries/`         | Create a new delivery     |
| GET    | `/api/v1/deliveries/`         | List user's deliveries    |
| GET    | `/api/v1/deliveries/{id}`     | Get delivery by ID        |
| PATCH  | `/api/v1/deliveries/{id}`     | Update delivery fields    |
| DELETE | `/api/v1/deliveries/{id}`     | Delete a delivery         |

### Risk Analysis
| Method | Path                              | Description                      |
|--------|-----------------------------------|----------------------------------|
| POST   | `/api/v1/risk/analyze/{id}`       | Trigger risk analysis            |
| GET    | `/api/v1/risk/history/{id}`       | Full analysis history            |
| GET    | `/api/v1/risk/latest/{id}`        | Most recent analysis             |
| GET    | `/api/v1/risk/summary/{id}`       | Human-readable risk summary      |
| POST   | `/api/v1/risk/rules`              | Create a custom risk rule        |
| GET    | `/api/v1/risk/rules`              | List all risk rules              |
| DELETE | `/api/v1/risk/rules/{id}`         | Delete a risk rule               |

### Events
| Method | Path                       | Description                |
|--------|----------------------------|----------------------------|
| GET    | `/api/v1/events/{id}`      | Event log for a delivery   |

All endpoints except `/health` require a `Bearer` token from Firebase Auth.

## Risk Scoring

The system produces a 0-100 risk score from four weighted dimensions:

| Dimension     | Weight | Data Source         | What It Measures                    |
|---------------|--------|---------------------|-------------------------------------|
| Weather       | 30%    | OpenWeatherMap      | Wind, visibility, severe conditions |
| News          | 25%    | NewsAPI             | Supply chain disruption articles    |
| Geopolitical  | 25%    | NewsAPI keywords    | Embargoes, conflicts, unrest        |
| Route         | 20%    | Haversine distance  | Origin-destination distance risk    |

Custom **Risk Rules** can be added via the API to adjust scoring based on specific field conditions (e.g., "if cargo_value > 100000, add 10 points").

### Risk Levels

| Score Range | Level    | Advisory                                              |
|-------------|----------|-------------------------------------------------------|
| 75-100      | Critical | Immediate attention — consider rerouting or delaying  |
| 50-74       | High     | Significant risks — review mitigation options         |
| 25-49       | Medium   | Moderate risks — monitor and prepare contingencies    |
| 0-24        | Low      | Favorable conditions — proceed with standard monitoring|

## Data Broker

All external API calls flow through the **Data Broker**, which provides:

- **In-memory LRU cache** with configurable TTL (default 5 minutes, 500 entries max)
- **Rate limiting** per minute across all external calls
- **Automatic retry** with exponential backoff (3 attempts via tenacity)

## License

MIT
