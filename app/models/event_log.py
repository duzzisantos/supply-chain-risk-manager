import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id = Column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    description = Column(Text)
    old_state = Column(JSON)
    new_state = Column(JSON)
    triggered_reanalysis = Column(String, default="false")
    created_at = Column(DateTime, default=datetime.utcnow)

    delivery = relationship("Delivery", back_populates="event_logs")
