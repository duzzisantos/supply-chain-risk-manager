from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.delivery import Delivery
from app.models.event_log import EventLog
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

router = APIRouter(prefix="/events", tags=["Event Logs"])


class EventLogResponse(BaseModel):
    id: UUID
    delivery_id: UUID
    event_type: str
    description: Optional[str]
    old_state: Optional[Dict[str, Any]]
    new_state: Optional[Dict[str, Any]]
    triggered_reanalysis: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{delivery_id}", response_model=List[EventLogResponse])
async def get_events(
    delivery_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = await db.get(Delivery, delivery_id)
    if not delivery or delivery.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Delivery not found")

    result = await db.execute(
        select(EventLog)
        .where(EventLog.delivery_id == delivery_id)
        .order_by(EventLog.created_at.desc())
    )
    return result.scalars().all()
