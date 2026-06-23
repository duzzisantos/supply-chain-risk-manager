from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID


class RiskFactor(BaseModel):
    category: str
    description: str
    severity: str
    score: float = Field(..., ge=0, le=100)


class RiskAnalysisResponse(BaseModel):
    id: UUID
    delivery_id: UUID
    overall_score: float
    weather_score: float
    news_score: float
    geopolitical_score: float
    route_score: float
    advisory: Optional[str]
    ai_summary: Optional[str]
    risk_factors: Dict[str, Any]
    weather_data: Dict[str, Any]
    news_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class RiskRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = Field(..., example="weather")
    condition: Dict[str, Any]
    weight: float = Field(1.0, ge=0, le=10)


class RiskRuleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    category: str
    condition: Dict[str, Any]
    weight: float
    is_active: str
    created_at: datetime

    class Config:
        from_attributes = True


class RiskSummary(BaseModel):
    delivery_id: UUID
    overall_score: float
    risk_level: str
    top_factors: List[RiskFactor]
    advisory: str
    recommended_actions: List[str]
