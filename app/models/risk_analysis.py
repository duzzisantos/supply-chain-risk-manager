import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class RiskAnalysis(Base):
    __tablename__ = "risk_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id = Column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=False, index=True)
    overall_score = Column(Float, nullable=False)
    weather_score = Column(Float, default=0.0)
    news_score = Column(Float, default=0.0)
    geopolitical_score = Column(Float, default=0.0)
    route_score = Column(Float, default=0.0)
    advisory = Column(Text)
    ai_summary = Column(Text)
    risk_factors = Column(JSON, default=dict)
    weather_data = Column(JSON, default=dict)
    news_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    delivery = relationship("Delivery", back_populates="risk_analyses")


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    category = Column(String, nullable=False)
    condition = Column(JSON, nullable=False)
    weight = Column(Float, default=1.0)
    is_active = Column(String, default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
