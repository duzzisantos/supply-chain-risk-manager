from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.models.delivery import DeliveryStatus


class DeliveryCreate(BaseModel):
    origin: str = Field(..., example="Lagos, Nigeria")
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lon: float = Field(..., ge=-180, le=180)
    destination: str = Field(..., example="Accra, Ghana")
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lon: float = Field(..., ge=-180, le=180)
    cargo_description: Optional[str] = None
    cargo_value: float = Field(0.0, ge=0)
    scheduled_departure: datetime
    scheduled_arrival: datetime


class DeliveryUpdate(BaseModel):
    origin: Optional[str] = None
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    destination: Optional[str] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    cargo_description: Optional[str] = None
    cargo_value: Optional[float] = None
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    status: Optional[DeliveryStatus] = None


class DeliveryResponse(BaseModel):
    id: UUID
    user_id: str
    origin: str
    origin_lat: float
    origin_lon: float
    destination: str
    dest_lat: float
    dest_lon: float
    cargo_description: Optional[str]
    cargo_value: float
    scheduled_departure: datetime
    scheduled_arrival: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
