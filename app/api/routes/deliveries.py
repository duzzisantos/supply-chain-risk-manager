from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.delivery import Delivery, DeliveryStatus
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from app.services.event_listener import on_delivery_updated

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


@router.post("/", response_model=DeliveryResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery(
    payload: DeliveryCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = Delivery(user_id=user["uid"], **payload.model_dump())
    db.add(delivery)
    await db.flush()
    await db.refresh(delivery)
    return delivery


@router.get("/", response_model=List[DeliveryResponse])
async def list_deliveries(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Delivery).where(Delivery.user_id == user["uid"]).order_by(Delivery.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{delivery_id}", response_model=DeliveryResponse)
async def get_delivery(
    delivery_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = await db.get(Delivery, delivery_id)
    if not delivery or delivery.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery


@router.patch("/{delivery_id}", response_model=DeliveryResponse)
async def update_delivery(
    delivery_id: UUID,
    payload: DeliveryUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = await db.get(Delivery, delivery_id)
    if not delivery or delivery.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Delivery not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return delivery

    old_values = {k: getattr(delivery, k) for k in update_data}
    for field, value in update_data.items():
        setattr(delivery, field, value)

    await on_delivery_updated(delivery_id, old_values, update_data, db)
    await db.flush()
    await db.refresh(delivery)
    return delivery


@router.delete("/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery(
    delivery_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = await db.get(Delivery, delivery_id)
    if not delivery or delivery.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Delivery not found")
    await db.delete(delivery)
