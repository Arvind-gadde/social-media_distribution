"""Contract Drafter Agent — AI-generated legal agreements.

Generates standardized contracts with FTC disclosure and payment terms.
Uses GPT-4o for structured legal document generation.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.business.models import (
    Collaboration, ContractDraft, ContractStatus,
)
from app.integrations.llm.provider import create_llm_provider, TaskType
from app.runtime.context import RunContext
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


CONTRACT_TEMPLATE_PROMPT = """Generate a professional influencer marketing contract based on these details:

Creator Details:
- Workspace: {workspace_name}
- Legal Name: {creator_legal_name}

Brand Details:
- Brand Name: {brand_name}
- Contact: {contact_name}

Deal Terms:
- Deliverables: {deliverables}
- Payment Amount: ${final_amount} {currency}
- Payment Type: {payment_type}
- Timeline: {timeline}

Generate a complete contract in Markdown format including:

1. **PARTIES** section with creator and brand details
2. **SCOPE OF WORK** with specific deliverables
3. **COMPENSATION** with payment terms (Net-30)
4. **CONTENT APPROVAL** with 48-hour review window
5. **FTC DISCLOSURE** requirements (must include #ad or #sponsored)
6. **USAGE RIGHTS** and exclusivity terms
7. **TERMINATION** clause
8. **SIGNATURES** section

Use professional legal language but keep it readable. Include standard creator-friendly terms:
- Creator retains content ownership
- Brand gets usage rights for specified period
- No exclusivity beyond 30 days unless specified
- Payment due within 30 days of content approval
- Either party can terminate with 7 days notice

Return ONLY the contract text in Markdown format, no additional commentary.
"""


async def generate_contract(
    db: AsyncSession,
    ctx: RunContext,
    collaboration_id: uuid.UUID,
) -> ContractDraft:
    """Generate AI contract draft for collaboration.
    
    Args:
        db: Database session
        ctx: Run context
        collaboration_id: Collaboration to generate contract for
        
    Returns:
        ContractDraft record
        
    Raises:
        ValueError: If collaboration not found or invalid state
    """
    # Fetch collaboration
    result = await db.execute(
        select(Collaboration).where(
            Collaboration.id == collaboration_id,
            Collaboration.workspace_id == ctx.workspace_id,
        )
    )
    collab = result.scalar_one_or_none()
    
    if not collab:
        raise ValueError(f"Collaboration {collaboration_id} not found")
    
    # Format deliverables
    deliverables_text = "\n".join([
        f"- {d.get('count', 1)}x {d.get('type', 'content')} on {d.get('platform', 'platform')}"
        for d in (collab.deliverables or [])
    ])
    
    # Format timeline
    timeline_text = "To be determined"
    if collab.deal_starts_at and collab.deal_ends_at:
        timeline_text = f"{collab.deal_starts_at.date()} to {collab.deal_ends_at.date()}"
    
    # Format prompt
    prompt = CONTRACT_TEMPLATE_PROMPT.format(
        workspace_name=f"Workspace {ctx.workspace_id}",  # TODO: Fetch actual workspace name
        creator_legal_name="Creator",  # TODO: Fetch from workspace settings
        brand_name=collab.brand_name,
        contact_name=collab.contact_name or "Brand Representative",
        deliverables=deliverables_text or "Content as agreed",
        final_amount=collab.final_amount or collab.offered_amount or 0,
        currency=collab.currency,
        payment_type=collab.payment_type.value if collab.payment_type else "flat_fee",
        timeline=timeline_text,
    )
    
    # Generate contract with GPT-4o
    from app.config import get_settings
    settings = get_settings()
    provider = create_llm_provider(
        openai_key=settings.OPENAI_API_KEY,
        gemini_key=settings.GEMINI_API_KEY,
        anthropic_key=settings.ANTHROPIC_API_KEY,
    )
    
    response = await provider.complete(
        task_type=TaskType.GENERATION,
        messages=[{"role": "user", "content": prompt}],
        workspace_id=ctx.workspace_id,
        temperature=0.3,
        max_tokens=2000,
        model_override="gpt-4o",
        db_session=db,
    )
    
    # Create contract draft
    contract = ContractDraft(
        collaboration_id=collaboration_id,
        workspace_id=ctx.workspace_id,
        contract_type="ai_generated",
        title=f"Influencer Marketing Agreement - {collab.brand_name}",
        content=response.content,
        status=ContractStatus.DRAFT,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(contract)
    
    # Usage is already recorded by provider.complete()
    # No need to call record_usage separately
    
    # Audit log
    audit = AuditService(db)
    await audit.log(
        workspace_id=ctx.workspace_id,
        actor_id=ctx.actor_id,
        action_type="contract_generated",
        resource_type="contract",
        resource_id=str(contract.id),
        correlation_id=ctx.correlation_id,
    )
    
    await db.commit()
    await db.refresh(contract)
    
    logger.info(
        f"Generated contract {contract.id} for collaboration {collaboration_id}",
        extra={"workspace_id": str(ctx.workspace_id), "contract_id": str(contract.id)},
    )
    
    return contract
