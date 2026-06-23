"""
Event listener that tracks state changes on deliveries and triggers re-analysis
when significant changes are detected.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.delivery import Delivery
from app.models.event_log import EventLog


REANALYSIS_TRIGGERS = {"status", "origin", "destination", "scheduled_departure", "scheduled_arrival"}


async def on_delivery_updated(
    delivery_id: UUID,
    old_values: dict,
    new_values: dict,
    db: AsyncSession,
) -> bool:
    """
    Log the state change and decide whether re-analysis is needed.
    Returns True if re-analysis was triggered.
    """
    changed_fields = {k for k in new_values if old_values.get(k) != new_values[k]}
    should_reanalyze = bool(changed_fields & REANALYSIS_TRIGGERS)

    def _serialize(val):
        return val.value if hasattr(val, "value") else str(val)

    event = EventLog(
        delivery_id=delivery_id,
        event_type="delivery_updated",
        description=f"Fields changed: {', '.join(changed_fields)}",
        old_state={k: _serialize(old_values.get(k)) for k in changed_fields},
        new_state={k: _serialize(new_values[k]) for k in changed_fields},
        triggered_reanalysis="true" if should_reanalyze else "false",
    )
    db.add(event)

    if should_reanalyze:
        from app.services.risk_analyzer import run_analysis
        await run_analysis(delivery_id, db)

    return should_reanalyze
