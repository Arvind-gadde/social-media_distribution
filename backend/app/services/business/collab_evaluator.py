"""Collaboration Evaluator Agent — AI-powered DM classification.

Reads unread DMs, classifies them, and creates Collaboration records for brand deals.
Uses Claude 3.5 Sonnet for high-quality business intelligence.
"""
import json
import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.business.models import (
    Collaboration, CollaborationStatus, CollaborationType,
    DMCategory, DMInbox, PaymentType,
)
from app.integrations.llm.provider import create_llm_provider, TaskType
from app.runtime.context import RunContext
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


EVALUATOR_PROMPT = """You are a business manager for a content creator. Analyze this DM and classify it.

DM Details:
- Platform: {platform}
- Sender: {sender_username} ({sender_followers} followers)
- Message: {message_text}

Classify this message and extract business details if applicable.

Return JSON with this exact structure:
{{
  "is_business": true/false,
  "category": "brand_deal" | "collab" | "fan" | "spam" | "hate" | "question" | "support",
  "priority": 1-10,
  "sentiment": -1.0 to 1.0,
  "summary": "Brief summary",
  "brand_name": "Brand name if business inquiry",
  "offered_amount": numeric value if mentioned,
  "deliverables": ["reel", "post", etc] if mentioned,
  "suggested_reply": "Professional reply suggestion"
}}

Be conservative with brand_deal classification. Only mark as brand_deal if:
- Clear sponsorship/partnership request
- Mentions payment or compensation
- Requests specific content deliverables
"""


async def evaluate_unread_dms(
    db: AsyncSession,
    ctx: RunContext,
    limit: int = 50,
) -> dict[str, int]:
    """Evaluate unread DMs with AI classification.
    
    Returns:
        Dict with counts: {"evaluated": 10, "brand_deals": 2, "errors": 0}
    """
    # Fetch unread DMs
    result = await db.execute(
        select(DMInbox)
        .where(
            DMInbox.workspace_id == ctx.workspace_id,
            DMInbox.ai_category == None,
        )
        .order_by(DMInbox.received_at.desc())
        .limit(limit)
    )
    dms = result.scalars().all()
    
    if not dms:
        return {"evaluated": 0, "brand_deals": 0, "errors": 0}
    
    stats = {"evaluated": 0, "brand_deals": 0, "errors": 0}
    
    # Get LLM provider
    from app.config import get_settings
    settings = get_settings()
    provider = create_llm_provider(
        openai_key=settings.OPENAI_API_KEY,
        gemini_key=settings.GEMINI_API_KEY,
        anthropic_key=settings.ANTHROPIC_API_KEY,
    )
    
    for dm in dms:
        try:
            # Format prompt
            prompt = EVALUATOR_PROMPT.format(
                platform=dm.platform,
                sender_username=dm.sender_username,
                sender_followers=dm.sender_followers_count or 0,
                message_text=dm.message_text,
            )
            
            # Call LLM (Claude for business intelligence)
            response = await provider.complete(
                task_type=TaskType.CLASSIFICATION,
                messages=[{"role": "user", "content": prompt}],
                workspace_id=ctx.workspace_id,
                temperature=0.3,
                max_tokens=500,
                db_session=db,
            )
            
            # Parse JSON response
            try:
                analysis = json.loads(response.content)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response for DM {dm.id}")
                stats["errors"] += 1
                continue
            
            # Update DM with analysis
            dm.is_business_inquiry = analysis.get("is_business", False)
            dm.ai_category = DMCategory(analysis.get("category", "unknown"))
            dm.ai_priority = analysis.get("priority", 5)
            dm.ai_sentiment = analysis.get("sentiment")
            dm.ai_summary = analysis.get("summary")
            dm.ai_suggested_reply = analysis.get("suggested_reply")
            
            stats["evaluated"] += 1
            
            # Usage is already recorded by provider.complete()
            # No need to call record_usage separately
            
            # Create Collaboration if brand deal
            if dm.is_business_inquiry and dm.ai_category == DMCategory.BRAND_DEAL:
                collab = Collaboration(
                    workspace_id=ctx.workspace_id,
                    collab_type=CollaborationType.BRAND_DEAL,
                    status=CollaborationStatus.INQUIRY,
                    brand_name=analysis.get("brand_name", dm.sender_username),
                    contact_handle=dm.sender_username,
                    contact_platform=dm.platform,
                    offered_amount=Decimal(str(analysis.get("offered_amount", 0))),
                    deliverables=analysis.get("deliverables", []),
                    source="inbound_dm",
                    source_platform=dm.platform,
                    source_dm_id=dm.id,
                )
                db.add(collab)
                dm.collaboration_id = collab.id
                stats["brand_deals"] += 1
                
                # Audit log
                audit = AuditService(db)
                await audit.log(
                    workspace_id=ctx.workspace_id,
                    actor_id=ctx.actor_id,
                    action_type="collaboration_created",
                    resource_type="collaboration",
                    resource_id=str(collab.id),
                    correlation_id=ctx.correlation_id,
                )
            
        except Exception as e:
            logger.error(
                f"Failed to evaluate DM {dm.id}: {e}",
                extra={"workspace_id": str(ctx.workspace_id), "dm_id": str(dm.id)},
            )
            stats["errors"] += 1
    
    await db.commit()
    return stats
