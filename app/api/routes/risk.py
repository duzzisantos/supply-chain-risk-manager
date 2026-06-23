from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.delivery import Delivery
from app.models.risk_analysis import RiskAnalysis, RiskRule
from app.schemas.risk import RiskAnalysisResponse, RiskRuleCreate, RiskRuleResponse, RiskSummary
from app.services.risk_analyzer import run_analysis

router = APIRouter(prefix="/risk", tags=["Risk Analysis"])


@router.post("/analyze/{delivery_id}", response_model=RiskAnalysisResponse)
async def trigger_analysis(
    delivery_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = await db.get(Delivery, delivery_id)
    if not delivery or delivery.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Delivery not found")

    analysis = await run_analysis(delivery_id, db)
    return analysis


@router.get("/history/{delivery_id}", response_model=List[RiskAnalysisResponse])
async def get_risk_history(
    delivery_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = await db.get(Delivery, delivery_id)
    if not delivery or delivery.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Delivery not found")

    result = await db.execute(
        select(RiskAnalysis)
        .where(RiskAnalysis.delivery_id == delivery_id)
        .order_by(RiskAnalysis.created_at.desc())
    )
    return result.scalars().all()


@router.get("/latest/{delivery_id}", response_model=RiskAnalysisResponse)
async def get_latest_risk(
    delivery_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = await db.get(Delivery, delivery_id)
    if not delivery or delivery.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Delivery not found")

    result = await db.execute(
        select(RiskAnalysis)
        .where(RiskAnalysis.delivery_id == delivery_id)
        .order_by(RiskAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="No risk analysis found — trigger one first")
    return analysis


@router.get("/summary/{delivery_id}", response_model=RiskSummary)
async def get_risk_summary(
    delivery_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    delivery = await db.get(Delivery, delivery_id)
    if not delivery or delivery.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Delivery not found")

    result = await db.execute(
        select(RiskAnalysis)
        .where(RiskAnalysis.delivery_id == delivery_id)
        .order_by(RiskAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="No risk analysis found")

    factors_raw = analysis.risk_factors or {}
    factors_list = factors_raw.get("factors", [])

    from app.schemas.risk import RiskFactor
    top_factors = sorted(factors_list, key=lambda f: f.get("score", 0), reverse=True)[:5]

    return RiskSummary(
        delivery_id=delivery_id,
        overall_score=analysis.overall_score,
        risk_level=factors_raw.get("risk_level", "unknown"),
        top_factors=[RiskFactor(**f) for f in top_factors],
        advisory=analysis.advisory or "",
        recommended_actions=factors_raw.get("recommended_actions", []),
    )


# --- Risk Rules CRUD ---

@router.post("/rules", response_model=RiskRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: RiskRuleCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rule = RiskRule(**payload.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.get("/rules", response_model=List[RiskRuleResponse])
async def list_rules(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RiskRule).order_by(RiskRule.created_at.desc()))
    return result.scalars().all()


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(RiskRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
