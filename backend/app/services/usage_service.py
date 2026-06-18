"""Usage Service - Durable cost accounting and LLM token tracking.

Phase 12: Audit & Governance
Tracks: LLM tokens, transcription minutes, image generations,
video processing minutes, publish attempts, storage growth.
"""
import uuid
import structlog
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal

from app.domains.control.models import UsageMeter, Workspace, BudgetPolicy

log = structlog.get_logger(__name__)


class UsageService:
    """Service for tracking and querying usage metrics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def record_usage(
        self,
        workspace_id: uuid.UUID,
        meter_type: str,
        quantity: float,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        source_run_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        cost_usd: float = 0.0,
    ) -> UsageMeter:
        """Record a usage event.
        
        Args:
            workspace_id: Workspace context
            meter_type: Type of usage (e.g., "llm_tokens_in", "llm_tokens_out", "publish_attempt")
            quantity: Raw quantity
            provider: Provider name (e.g., "openai", "anthropic")
            model: Model name (e.g., "gpt-4o", "claude-3.5-sonnet")
            source_run_id: Agent run or job ID that caused this usage
            source_type: Type of source (e.g., "agent_run", "publish_job")
            cost_usd: Cost in USD
        
        Returns:
            Created UsageMeter instance
        """
        usage_meter = UsageMeter(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            meter_type=meter_type,
            quantity=quantity,
            billable_quantity=quantity,  # Can be adjusted based on tier
            cost_usd=cost_usd,
            provider=provider,
            model=model,
            source_run_id=source_run_id,
            source_type=source_type,
            recorded_at=datetime.now(timezone.utc),
        )
        
        self.db.add(usage_meter)
        await self.db.flush()
        
        log.info(
            "usage_recorded",
            usage_id=str(usage_meter.id),
            workspace_id=str(workspace_id),
            meter_type=meter_type,
            quantity=quantity,
            cost_usd=cost_usd,
            provider=provider,
            model=model,
        )
        
        return usage_meter
    
    async def get_workspace_usage_summary(
        self,
        workspace_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get usage summary for a workspace.
        
        Args:
            workspace_id: Workspace to query
            start_date: Start of period (default: beginning of current month)
            end_date: End of period (default: now)
        
        Returns:
            Dictionary with usage summary by meter type
        """
        if start_date is None:
            now = datetime.now(timezone.utc)
            start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        query = (
            select(
                UsageMeter.meter_type,
                func.sum(UsageMeter.quantity).label('total_quantity'),
                func.sum(UsageMeter.cost_usd).label('total_cost'),
                func.count(UsageMeter.id).label('event_count'),
            )
            .where(
                UsageMeter.workspace_id == workspace_id,
                UsageMeter.recorded_at >= start_date,
                UsageMeter.recorded_at <= end_date,
            )
            .group_by(UsageMeter.meter_type)
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        summary = {
            "workspace_id": str(workspace_id),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "by_meter_type": {},
            "total_cost_usd": 0.0,
        }
        
        for row in rows:
            summary["by_meter_type"][row.meter_type] = {
                "quantity": float(row.total_quantity),
                "cost_usd": float(row.total_cost),
                "event_count": row.event_count,
            }
            summary["total_cost_usd"] += float(row.total_cost)
        
        return summary
    
    async def check_budget_exceeded(
        self,
        workspace_id: uuid.UUID,
    ) -> tuple[bool, Optional[dict]]:
        """Check if workspace has exceeded budget limits.
        
        Args:
            workspace_id: Workspace to check
        
        Returns:
            Tuple of (exceeded: bool, details: dict)
        """
        # Get budget policy
        budget_query = select(BudgetPolicy).where(
            BudgetPolicy.workspace_id == workspace_id,
            BudgetPolicy.is_active == True,
        )
        budget_result = await self.db.execute(budget_query)
        budget_policy = budget_result.scalar_one_or_none()
        
        if not budget_policy:
            return False, None
        
        # Get current month usage
        summary = await self.get_workspace_usage_summary(workspace_id)
        
        # Check LLM budget
        llm_cost = 0.0
        for meter_type, data in summary["by_meter_type"].items():
            if meter_type.startswith("llm_"):
                llm_cost += data["cost_usd"]
        
        llm_exceeded = llm_cost >= budget_policy.monthly_llm_budget_usd
        llm_pct = (llm_cost / budget_policy.monthly_llm_budget_usd * 100) if budget_policy.monthly_llm_budget_usd > 0 else 0
        
        # Check media budget
        media_cost = 0.0
        for meter_type, data in summary["by_meter_type"].items():
            if meter_type.startswith("media_") or meter_type.startswith("video_"):
                media_cost += data["cost_usd"]
        
        media_exceeded = media_cost >= budget_policy.monthly_media_budget_usd
        media_pct = (media_cost / budget_policy.monthly_media_budget_usd * 100) if budget_policy.monthly_media_budget_usd > 0 else 0
        
        exceeded = llm_exceeded or media_exceeded
        
        details = {
            "llm": {
                "current": llm_cost,
                "budget": budget_policy.monthly_llm_budget_usd,
                "percentage": llm_pct,
                "exceeded": llm_exceeded,
            },
            "media": {
                "current": media_cost,
                "budget": budget_policy.monthly_media_budget_usd,
                "percentage": media_pct,
                "exceeded": media_exceeded,
            },
            "hard_stop": budget_policy.hard_stop_on_budget,
            "auto_downgrade_threshold": budget_policy.auto_downgrade_threshold_pct,
        }
        
        if exceeded:
            log.warning(
                "budget_exceeded",
                workspace_id=str(workspace_id),
                llm_cost=llm_cost,
                media_cost=media_cost,
                details=details,
            )
        
        return exceeded, details


# Convenience functions for common usage tracking

async def track_llm_usage(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    source_run_id: Optional[uuid.UUID] = None,
) -> tuple[UsageMeter, UsageMeter]:
    """Track LLM token usage (input and output separately)."""
    service = UsageService(db)
    
    meter_in = await service.record_usage(
        workspace_id=workspace_id,
        meter_type="llm_tokens_in",
        quantity=float(tokens_in),
        provider=provider,
        model=model,
        source_run_id=source_run_id,
        source_type="agent_run",
        cost_usd=cost_usd * 0.3,  # Rough split: 30% input, 70% output
    )
    
    meter_out = await service.record_usage(
        workspace_id=workspace_id,
        meter_type="llm_tokens_out",
        quantity=float(tokens_out),
        provider=provider,
        model=model,
        source_run_id=source_run_id,
        source_type="agent_run",
        cost_usd=cost_usd * 0.7,
    )
    
    return meter_in, meter_out


async def track_publish_attempt(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    platform: str,
    success: bool,
) -> UsageMeter:
    """Track a publish attempt."""
    service = UsageService(db)
    
    return await service.record_usage(
        workspace_id=workspace_id,
        meter_type=f"publish_attempt_{platform}",
        quantity=1.0,
        provider=platform,
        source_type="publish_job",
        cost_usd=0.0,  # No direct cost, but tracked for rate limiting
    )


async def track_video_processing(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    duration_seconds: int,
    cost_usd: float,
) -> UsageMeter:
    """Track video processing usage."""
    service = UsageService(db)
    
    return await service.record_usage(
        workspace_id=workspace_id,
        meter_type="video_processing_seconds",
        quantity=float(duration_seconds),
        provider="ffmpeg",
        source_type="media_job",
        cost_usd=cost_usd,
    )


async def track_transcription(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    duration_minutes: float,
    cost_usd: float,
) -> UsageMeter:
    """Track transcription usage."""
    service = UsageService(db)
    
    return await service.record_usage(
        workspace_id=workspace_id,
        meter_type="transcription_minutes",
        quantity=duration_minutes,
        provider="openai_whisper",
        source_type="media_job",
        cost_usd=cost_usd,
    )
