"""Agent Nodes - Individual agent implementations for LangGraph workflow.

Phase 13: Agent Orchestration

Implements all 14 agents from the ContentFlow blueprint:
1. Niche Intelligence Agent
2. Trend Detection Agent
3. Analytics Intelligence Agent
4. Competitor Intelligence Agent
5. Content Research & Ideation Agent
6. Goal & Accountability Agent
7. Collaboration & Business Agent
8. News & Research Agent
9. Tips, Tricks & Platform Algorithm Agent
10. Smart Scheduling Agent
11. Growth & Engagement Optimization Agent
12. Video Intelligence Agent
13. Predictive Virality Agent
14. Agent Orchestrator (Master)
"""
import time
import uuid
import structlog
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Awaitable, Callable
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_event_bus import publish_agent_event
from app.services.llm.router import router, TaskType
from app.services.usage_service import UsageService
from app.services.audit_service import AuditService
from app.services.llm.client import get_llm_client
from app.services.cache.cache_manager import get_cache_manager
from app.runtime.correlation import get_correlation_id
from .state import AgentState

log = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# NODE EVENT DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════

NodeFn = Callable[[AgentState, AsyncSession], Awaitable[AgentState]]


def with_node_events(agent_type: str | None = None) -> Callable[[NodeFn], NodeFn]:
    """Publish agent_node_started/completed/failed around an agent node.

    Publishing is best-effort — Redis outages must not block agent execution.
    """

    def decorator(func: NodeFn) -> NodeFn:
        resolved_type = agent_type or func.__name__.removesuffix("_agent")

        @wraps(func)
        async def wrapper(state: AgentState, db: AsyncSession) -> AgentState:
            workspace_id = state.get("workspace_id")
            correlation_id = state.get("correlation_id") or get_correlation_id()
            insights_before = len(state.get("insights", []) or [])
            ideas_before = len(state.get("content_ideas", []) or [])
            errors_before = len(state.get("errors", []) or [])
            started_monotonic = time.monotonic()

            if workspace_id:
                await publish_agent_event(
                    workspace_id=workspace_id,
                    event_type="agent_node_started",
                    agent_type=resolved_type,
                    correlation_id=correlation_id,
                    data={"agent_type": resolved_type},
                )

            try:
                result_state = await func(state, db)
            except Exception as exc:
                duration_ms = int((time.monotonic() - started_monotonic) * 1000)
                if workspace_id:
                    await publish_agent_event(
                        workspace_id=workspace_id,
                        event_type="agent_node_failed",
                        agent_type=resolved_type,
                        correlation_id=correlation_id,
                        data={
                            "agent_type": resolved_type,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                            "duration_ms": duration_ms,
                        },
                    )
                raise

            duration_ms = int((time.monotonic() - started_monotonic) * 1000)
            if isinstance(result_state, dict):
                insights_after = len(result_state.get("insights", []) or [])
                ideas_after = len(result_state.get("content_ideas", []) or [])
                errors_after = len(result_state.get("errors", []) or [])
            else:
                insights_after = insights_before
                ideas_after = ideas_before
                errors_after = errors_before

            if workspace_id:
                await publish_agent_event(
                    workspace_id=workspace_id,
                    event_type="agent_node_completed",
                    agent_type=resolved_type,
                    correlation_id=correlation_id,
                    data={
                        "agent_type": resolved_type,
                        "duration_ms": duration_ms,
                        "insights_added": max(0, insights_after - insights_before),
                        "ideas_added": max(0, ideas_after - ideas_before),
                        "errors_added": max(0, errors_after - errors_before),
                    },
                )
            return result_state

        return wrapper

    return decorator


async def publish_node_progress(
    state: AgentState,
    agent_type: str,
    step: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Publish a fine-grained progress event from inside an agent node.

    Use sparingly for long-running stages so the UI can show step-by-step progress.
    """
    workspace_id = state.get("workspace_id")
    if not workspace_id:
        return
    await publish_agent_event(
        workspace_id=workspace_id,
        event_type="agent_node_progress",
        agent_type=agent_type,
        correlation_id=state.get("correlation_id"),
        data={"agent_type": agent_type, "step": step, **(data or {})},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def track_agent_step(
    agent_name: str,
    state: AgentState,
    db: AsyncSession,
    provider: str,
    model: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> None:
    """Track agent step execution with usage metering."""
    usage_service = UsageService(db)
    
    # Track input tokens
    if tokens_in > 0:
        await usage_service.record_usage(
            workspace_id=uuid.UUID(state["workspace_id"]),
            meter_type="llm_tokens_in",
            quantity=tokens_in,
            provider=provider,
            model=model,
            source_run_id=None,  # TODO: Link to agent_run_id
        )
    
    # Track output tokens
    if tokens_out > 0:
        await usage_service.record_usage(
            workspace_id=uuid.UUID(state["workspace_id"]),
            meter_type="llm_tokens_out",
            quantity=tokens_out,
            provider=provider,
            model=model,
            source_run_id=None,
        )
    
    log.info(
        f"agent.{agent_name}.step_tracked",
        workspace_id=state["workspace_id"],
        provider=provider,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 1: NICHE INTELLIGENCE AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def niche_intelligence_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Niche Intelligence Agent - Learns and adapts to creator's content niche.
    
    Runs: Every 6 hours
    
    Does:
    - Analyzes creator's past content performance by topic
    - Identifies which content pillars perform best
    - Suggests niche expansion or refinement
    - Builds creator's unique audience interest graph
    - Updates semantic embeddings in Qdrant
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.domains.execution.models import ContentProject
    from app.services.niche.niche_analyzer import NicheAnalyzer
    import json
    
    log.info("agent.niche_intelligence.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (6 hours TTL)
    cache_key = f"niche_{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')}"
    cached = await cache.get_cached_result(
        agent_name="niche_intelligence",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.niche_intelligence.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["niche_intelligence"] = cached
        state["active_agents"].append("niche_intelligence")
        
        # Generate insights from cached data
        if cached.get("pillars"):
            for pillar in cached["pillars"][:2]:  # Top 2 pillars
                if pillar.get("strength_score", 0) > 0.7:
                    state["insights"].append({
                        "type": "niche_insight",
                        "priority": 6,
                        "title": f"🎯 Strong pillar: {pillar['topic']}",
                        "body": f"Engagement rate: {pillar['avg_engagement_rate']:.2%}. Keep creating content on this topic!",
                        "action": {"type": "view_analytics"},
                    })
        
        return state
    
    try:
        # Get workspace
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        # Get content from last 90 days
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        content_query = select(ContentProject).where(
            ContentProject.workspace_id == workspace_id,
            ContentProject.created_at >= ninety_days_ago,
        ).order_by(ContentProject.created_at.desc()).limit(100)
        
        content_result = await db.execute(content_query)
        content_items = content_result.scalars().all()
        
        if not content_items:
            log.info("agent.niche_intelligence.no_data", workspace_id=state["workspace_id"])
            
            empty_result = {
                "has_data": False,
                "message": "No content data available yet. Start creating content to analyze your niche!",
                "provider": None,
                "model": None,
            }
            
            state["agent_results"]["niche_intelligence"] = empty_result
            state["active_agents"].append("niche_intelligence")
            
            return state
        
        # Convert to dict format for analyzer
        content_data = []
        for item in content_items:
            content_data.append({
                "title": item.title or "Untitled",
                "topics": [],  # TODO: Extract from content metadata
                "tags": [],
                "views": 0,  # TODO: Get from analytics
                "likes": 0,
                "comments": 0,
                "shares": 0,
            })
        
        # Initialize analyzer
        analyzer = NicheAnalyzer()
        
        log.info("agent.niche_intelligence.analyzing",
                workspace_id=state["workspace_id"],
                content_count=len(content_data))
        
        # Analyze content performance
        performance = analyzer.analyze_content_performance(content_data)
        
        # Identify content pillars
        pillars = analyzer.identify_content_pillars(content_data, min_content_count=3)
        
        # Calculate niche focus score
        focus_score = analyzer.calculate_niche_focus_score(content_data)
        
        # Build audience interest graph
        interest_graph = analyzer.build_audience_interest_graph(content_data)
        
        # Get expansion suggestions
        expansion_suggestions = analyzer.suggest_niche_expansion(pillars)
        
        # Use LLM to generate personalized recommendations
        provider_name, model = router.get_provider(TaskType.LONG_CONTEXT_ANALYSIS)
        llm_client = get_llm_client()
        
        analysis_prompt = f"""You are a content strategy expert. Analyze this creator's niche performance and provide actionable recommendations.

Content Analysis:
- Total content pieces: {performance['total_content']}
- Unique topics: {performance['unique_topics']}
- Niche focus score: {focus_score:.2f} (0=diverse, 1=focused)

Top Performing Topics:
{json.dumps(performance['top_topics'][:5], indent=2)}

Content Pillars:
{json.dumps(pillars[:5], indent=2)}

Provide analysis in JSON format:
{{
    "niche_assessment": "Brief assessment of their niche focus",
    "strengths": ["strength 1", "strength 2"],
    "opportunities": ["opportunity 1", "opportunity 2"],
    "recommendations": ["recommendation 1", "recommendation 2"]
}}

Focus on:
1. Content consistency and pillar strength
2. Opportunities for niche expansion
3. Actionable next steps"""
        
        try:
            response = await llm_client.complete(
                provider=provider_name,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert content strategist who helps creators optimize their niche focus."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            # Parse LLM response
            try:
                llm_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                log.warning("agent.niche_intelligence.llm_parse_failed",
                           workspace_id=state["workspace_id"])
                llm_analysis = {
                    "niche_assessment": "Analysis in progress",
                    "strengths": ["Consistent content creation"],
                    "opportunities": ["Explore related topics"],
                    "recommendations": ["Continue building content library"],
                }
            
            # Build result
            result = {
                "has_data": True,
                "content_analyzed": len(content_data),
                "analysis_period_days": 90,
                "niche_focus_score": focus_score,
                "unique_topics": performance["unique_topics"],
                "top_topics": performance["top_topics"][:10],
                "pillars": pillars,
                "pillar_count": len(pillars),
                "interest_graph": interest_graph,
                "expansion_suggestions": expansion_suggestions,
                "llm_analysis": llm_analysis,
                "provider": provider_name,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Track usage
            await track_agent_step(
                "niche_intelligence", state, db, provider_name, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 6 hours
            await cache.cache_result(
                agent_name="niche_intelligence",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=21600,  # 6 hours
            )
            
            log.info("agent.niche_intelligence.completed",
                     workspace_id=state["workspace_id"],
                     pillars_found=len(pillars),
                     focus_score=focus_score,
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.niche_intelligence.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback without LLM analysis
            result = {
                "has_data": True,
                "content_analyzed": len(content_data),
                "analysis_period_days": 90,
                "niche_focus_score": focus_score,
                "unique_topics": performance["unique_topics"],
                "top_topics": performance["top_topics"][:10],
                "pillars": pillars,
                "pillar_count": len(pillars),
                "interest_graph": interest_graph,
                "expansion_suggestions": expansion_suggestions,
                "llm_analysis": {
                    "niche_assessment": "Basic analysis available",
                    "strengths": ["Content creation consistency"],
                    "opportunities": ["Niche refinement"],
                    "recommendations": ["Review top performing topics"],
                },
                "provider": None,
                "model": None,
                "error": "LLM analysis unavailable, showing basic metrics",
            }
        
        state["agent_results"]["niche_intelligence"] = result
        state["active_agents"].append("niche_intelligence")
        
        # Generate insights for strong pillars
        for pillar in pillars[:3]:  # Top 3 pillars
            if pillar.get("strength_score", 0) > 0.7:
                state["insights"].append({
                    "type": "niche_insight",
                    "priority": 6,
                    "title": f"🎯 Strong pillar: {pillar['topic']}",
                    "body": f"Engagement rate: {pillar['avg_engagement_rate']:.2%}. This topic resonates with your audience!",
                    "action": {"type": "view_analytics"},
                })
        
        # Generate insight for niche focus
        if focus_score < 0.5:
            state["insights"].append({
                "type": "niche_warning",
                "priority": 7,
                "title": "📊 Niche focus could be stronger",
                "body": f"Focus score: {focus_score:.2f}. Consider concentrating on 3-5 core topics for better audience building.",
                "action": {"type": "view_niche_analysis"},
            })
        elif focus_score > 0.8:
            state["insights"].append({
                "type": "niche_success",
                "priority": 5,
                "title": "🎯 Excellent niche focus!",
                "body": f"Focus score: {focus_score:.2f}. Your content is highly focused and consistent.",
                "action": {"type": "view_niche_analysis"},
            })
    
    except Exception as e:
        log.error("agent.niche_intelligence.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["niche_intelligence"] = {
            "has_data": False,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("niche_intelligence")
        state["errors"].append(f"niche_intelligence: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 2: TREND DETECTION AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def trend_detection_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Trend Detection Agent - Catches trends before they peak.
    
    Runs: Every 30 minutes
    
    Sources:
    - TikTok Discover (Playwright)
    - Twitter/X Trending (API + scraping)
    - YouTube Trending
    - Google Trends API
    - Reddit rising posts
    - Instagram Explore
    - Pinterest Trends
    
    Does:
    - Scores each trend 0-100 (heat score)
    - Predicts when trend will peak
    - Matches trends to user's niche
    - Generates "how to make this content" brief
    - Alerts if trend velocity is exceptional
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.services.trends.trend_detector import TrendDetector
    from app.config import get_settings
    settings = get_settings()
    import json
    
    log.info("agent.trend_detection.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (30 minutes TTL)
    cache_key = f"trends_{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M')[:16]}"  # Round to 30 min
    cached = await cache.get_cached_result(
        agent_name="trend_detection",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.trend_detection.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["trend_detection"] = cached
        state["active_agents"].append("trend_detection")
        
        # Generate insights from cached data
        if cached.get("trends"):
            for trend in cached["trends"]:
                if trend.get("heat_score", 0) > 85:
                    state["insights"].append({
                        "type": "trend_alert",
                        "priority": 9,
                        "title": f"🔥 Trending NOW: {trend['title']}",
                        "body": f"Heat score: {trend['heat_score']}/100. {trend.get('how_to_brief', '')}",
                        "action": {"type": "create_content", "trend_data": trend},
                    })
        
        return state
    
    try:
        # Get workspace to determine niche
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        # Default niche keywords and subreddits (can be customized per workspace)
        niche_keywords = ["AI", "content creation", "productivity", "creator tools"]
        niche_subreddits = ["technology", "productivity", "SideProject"]
        
        # Initialize trend detector
        detector = TrendDetector(
            reddit_client_id=getattr(settings, 'REDDIT_CLIENT_ID', None),
            reddit_client_secret=getattr(settings, 'REDDIT_CLIENT_SECRET', None),
            youtube_api_key=getattr(settings, 'YOUTUBE_API_KEY', None),
        )
        
        # Fetch trends from all sources
        log.info("agent.trend_detection.fetching_sources",
                workspace_id=state["workspace_id"],
                keywords=niche_keywords,
                subreddits=niche_subreddits)
        
        all_trends = await detector.fetch_all_trends(
            niche_keywords=niche_keywords,
            niche_subreddits=niche_subreddits,
        )
        
        if not all_trends:
            log.warning("agent.trend_detection.no_trends_found",
                       workspace_id=state["workspace_id"])
            
            empty_result = {
                "trends_found": 0,
                "message": "No trends detected at this time. Check back in 30 minutes.",
                "provider": None,
                "model": None,
            }
            
            state["agent_results"]["trend_detection"] = empty_result
            state["active_agents"].append("trend_detection")
            
            return state
        
        # Score and normalize trends
        scored_trends = []
        for trend in all_trends:
            # Calculate normalized metrics
            velocity = trend.get("velocity", 0.5)
            volume = min(trend.get("current_interest", 50) / 100, 1.0)
            recency = 0.9  # Assume recent since we just fetched
            engagement = min(trend.get("engagement_score", 1000) / 5000, 1.0)
            diversity = 0.5  # Single source for now
            
            # Calculate heat score
            heat_score = detector.calculate_trend_score(
                velocity=velocity,
                volume=volume,
                recency=recency,
                engagement=engagement,
                diversity=diversity,
            )
            
            # Predict peak timing
            peak_predicted_at = detector.predict_peak_timing(
                velocity=velocity,
                current_volume=volume,
            )
            
            scored_trends.append({
                "title": trend.get("title", "Untitled Trend"),
                "source": trend.get("source", "unknown"),
                "trend_type": trend.get("trend_type", "topic"),
                "heat_score": round(heat_score, 2),
                "velocity": round(velocity, 3),
                "peak_predicted_at": peak_predicted_at.isoformat(),
                "platforms": trend.get("platforms", ["multiple"]),
                "raw_data": {
                    "current_interest": trend.get("current_interest"),
                    "score": trend.get("score"),
                    "views_text": trend.get("views_text"),
                },
            })
        
        # Sort by heat score
        scored_trends.sort(key=lambda x: x["heat_score"], reverse=True)
        
        # Take top 20 trends for LLM analysis
        top_trends = scored_trends[:20]
        
        # Use LLM to analyze trends and generate "how to" briefs
        provider, model = router.get_provider(TaskType.TREND_ANALYSIS)
        llm_client = get_llm_client()
        
        analysis_prompt = f"""You are a trend analysis expert. Analyze these trending topics and provide actionable content creation briefs.

Trends Data:
{json.dumps(top_trends[:10], indent=2)}

For each trend, provide:
1. Niche match score (0-1) - how relevant is this to content creators
2. "How to make this content" brief (2-3 sentences, specific and actionable)
3. Best platform for this trend
4. Suggested hashtags (3-5)
5. Estimated virality potential (0-1)

Return JSON:
{{
    "trends": [
        {{
            "title": "...",
            "niche_match": 0.95,
            "how_to_brief": "Create a 60s video demonstrating...",
            "best_platform": "tiktok",
            "hashtags": ["#...", "#..."],
            "estimated_virality": 0.85
        }}
    ]
}}

Focus on trends that are:
- Rising (not peaked yet)
- Actionable (creator can make content quickly)
- High engagement potential"""
        
        try:
            response = await llm_client.complete(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert trend analyst who identifies viral content opportunities for creators."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Parse LLM response
            try:
                analysis = json.loads(response.content)
                analyzed_trends = analysis.get("trends", [])
                
                # Merge LLM analysis with scored trends
                for i, analyzed in enumerate(analyzed_trends):
                    if i < len(top_trends):
                        top_trends[i].update({
                            "niche_match": analyzed.get("niche_match", 0.5),
                            "how_to_brief": analyzed.get("how_to_brief", ""),
                            "best_platform": analyzed.get("best_platform", "instagram"),
                            "hashtags": analyzed.get("hashtags", []),
                            "estimated_virality": analyzed.get("estimated_virality", 0.5),
                        })
            
            except json.JSONDecodeError:
                log.warning("agent.trend_detection.llm_parse_failed",
                           workspace_id=state["workspace_id"])
                # Use trends without LLM enhancement
                for trend in top_trends:
                    trend.update({
                        "niche_match": 0.7,
                        "how_to_brief": f"Create content about: {trend['title']}",
                        "best_platform": "instagram",
                        "hashtags": [],
                        "estimated_virality": 0.6,
                    })
            
            # Filter to high-relevance trends
            relevant_trends = [t for t in top_trends if t.get("niche_match", 0) > 0.6]
            
            # Build result
            result = {
                "trends_found": len(all_trends),
                "analyzed_trends": len(top_trends),
                "relevant_trends": len(relevant_trends),
                "top_trend_score": top_trends[0]["heat_score"] if top_trends else 0,
                "trends": relevant_trends[:10],  # Return top 10 relevant
                "provider": provider,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Track usage
            await track_agent_step(
                "trend_detection", state, db, provider, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 30 minutes
            await cache.cache_result(
                agent_name="trend_detection",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=1800,  # 30 minutes
            )
            
            log.info("agent.trend_detection.completed",
                     workspace_id=state["workspace_id"],
                     trends_found=len(all_trends),
                     relevant_trends=len(relevant_trends),
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.trend_detection.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback without LLM analysis
            result = {
                "trends_found": len(all_trends),
                "analyzed_trends": len(top_trends),
                "relevant_trends": len(top_trends),
                "top_trend_score": top_trends[0]["heat_score"] if top_trends else 0,
                "trends": top_trends[:10],
                "provider": None,
                "model": None,
                "error": "LLM analysis unavailable, showing raw trends",
            }
        
        state["agent_results"]["trend_detection"] = result
        state["active_agents"].append("trend_detection")
        
        # Generate insights for high-velocity trends
        for trend in result.get("trends", [])[:5]:  # Top 5 only
            if trend.get("heat_score", 0) > 85:
                state["insights"].append({
                    "type": "trend_alert",
                    "priority": 9,
                    "title": f"🔥 Trending NOW: {trend['title']}",
                    "body": f"Heat score: {trend['heat_score']}/100. {trend.get('how_to_brief', 'Act fast on this trend!')}",
                    "action": {"type": "create_content", "trend_data": trend},
                })
            elif trend.get("heat_score", 0) > 70:
                state["insights"].append({
                    "type": "trend_opportunity",
                    "priority": 7,
                    "title": f"📈 Rising: {trend['title']}",
                    "body": f"Heat score: {trend['heat_score']}/100. {trend.get('how_to_brief', 'Good opportunity!')}",
                    "action": {"type": "create_content", "trend_data": trend},
                })
    
    except Exception as e:
        log.error("agent.trend_detection.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["trend_detection"] = {
            "trends_found": 0,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("trend_detection")
        state["errors"].append(f"trend_detection: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 3: ANALYTICS INTELLIGENCE AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def analytics_intelligence_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Analytics Intelligence Agent - Turns raw numbers into actionable intelligence.
    
    Runs: Daily (deep), Real-time (on post publish)
    
    Does:
    - Computes engagement rate benchmarks vs niche average
    - Identifies best performing content types, hooks, lengths
    - Analyzes comment intelligence (questions, complaints, suggestions)
    - Detects optimal posting time
    - Generates weekly performance report
    - Flags underperforming content and diagnoses why
    - Revenue attribution across content pieces
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, func, and_
    from app.domains.execution.models import ContentProject
    import json
    
    log.info("agent.analytics_intelligence.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (1 hour TTL)
    cache_key = f"analytics_{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')}"
    cached = await cache.get_cached_result(
        agent_name="analytics_intelligence",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.analytics_intelligence.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["analytics_intelligence"] = cached
        state["active_agents"].append("analytics_intelligence")
        
        # Generate insights from cached data
        if cached.get("insights"):
            state["insights"].extend(cached["insights"])
        
        return state
    
    # Query content performance data (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    try:
        # Get content projects with performance data
        content_query = select(ContentProject).where(
            and_(
                ContentProject.workspace_id == workspace_id,
                ContentProject.created_at >= thirty_days_ago,
            )
        ).order_by(ContentProject.created_at.desc()).limit(50)
        
        result = await db.execute(content_query)
        content_items = result.scalars().all()
        
        if not content_items:
            log.info("agent.analytics_intelligence.no_data", workspace_id=state["workspace_id"])
            
            # Return empty result
            empty_result = {
                "has_data": False,
                "message": "No content data available yet. Start creating content to see analytics!",
                "provider": None,
                "model": None,
            }
            
            state["agent_results"]["analytics_intelligence"] = empty_result
            state["active_agents"].append("analytics_intelligence")
            
            return state
        
        # Calculate basic metrics
        total_content = len(content_items)
        
        # Prepare data for LLM analysis
        content_summary = []
        for item in content_items[:20]:  # Limit to 20 most recent
            content_summary.append({
                "title": item.title or "Untitled",
                "status": item.status.value if hasattr(item.status, 'value') else str(item.status),
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })
        
        # Use LLM to analyze patterns
        provider, model = router.get_provider(TaskType.LONG_CONTEXT_ANALYSIS)
        llm_client = get_llm_client()
        
        analysis_prompt = f"""Analyze this creator's content performance data and provide actionable insights.

Content Summary (last 30 days):
- Total content pieces: {total_content}
- Recent content: {json.dumps(content_summary, indent=2)}

Provide analysis in JSON format:
{{
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "content_patterns": "description of patterns observed",
    "recommendations": ["recommendation 1", "recommendation 2"],
    "best_practices": ["practice 1", "practice 2"]
}}

Focus on:
1. Content creation consistency
2. Content type patterns
3. Actionable recommendations for improvement
"""
        
        try:
            response = await llm_client.complete(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert content analytics advisor. Provide concise, actionable insights based on creator data."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            # Parse LLM response
            try:
                analysis = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback if LLM doesn't return valid JSON
                analysis = {
                    "key_insights": ["Content analysis in progress"],
                    "content_patterns": response.content[:200],
                    "recommendations": ["Continue creating content consistently"],
                    "best_practices": ["Focus on quality over quantity"],
                }
            
            # Build result
            result = {
                "has_data": True,
                "total_content": total_content,
                "analysis_period_days": 30,
                "key_insights": analysis.get("key_insights", []),
                "content_patterns": analysis.get("content_patterns", ""),
                "recommendations": analysis.get("recommendations", []),
                "best_practices": analysis.get("best_practices", []),
                "provider": provider,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Generate insights for state
            insights = []
            for i, insight in enumerate(analysis.get("key_insights", [])[:3]):
                insights.append({
                    "type": "analytics_insight",
                    "priority": 7 - i,
                    "title": f"📊 Analytics Insight #{i+1}",
                    "body": insight,
                    "action": {"type": "view_analytics"},
                })
            
            result["insights"] = insights
            
            # Track usage
            await track_agent_step(
                "analytics_intelligence", state, db, provider, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 1 hour
            await cache.cache_result(
                agent_name="analytics_intelligence",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=3600,
            )
            
            log.info("agent.analytics_intelligence.completed",
                     workspace_id=state["workspace_id"],
                     insights_count=len(insights),
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.analytics_intelligence.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback to basic analysis without LLM
            result = {
                "has_data": True,
                "total_content": total_content,
                "analysis_period_days": 30,
                "key_insights": [
                    f"You've created {total_content} content pieces in the last 30 days",
                    "Keep up the consistent content creation",
                ],
                "recommendations": [
                    "Continue your current content strategy",
                    "Track engagement metrics as you publish",
                ],
                "provider": None,
                "model": None,
                "error": "LLM analysis unavailable, showing basic metrics",
            }
            
            insights = [{
                "type": "analytics_insight",
                "priority": 7,
                "title": f"📊 {total_content} content pieces created",
                "body": "You're building a solid content library. Keep going!",
                "action": {"type": "view_analytics"},
            }]
            
            result["insights"] = insights
        
        state["agent_results"]["analytics_intelligence"] = result
        state["active_agents"].append("analytics_intelligence")
        state["insights"].extend(insights)
    
    except Exception as e:
        log.error("agent.analytics_intelligence.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["analytics_intelligence"] = {
            "has_data": False,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("analytics_intelligence")
        state["errors"].append(f"analytics_intelligence: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 4: COMPETITOR INTELLIGENCE AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def competitor_intelligence_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Competitor Intelligence Agent - Tracks what competitors post and what works.
    
    Runs: Every 4 hours
    
    Does:
    - Scrapes competitor profiles (Playwright + rotating proxies)
    - Tracks every new post within 30 mins
    - Scores competitor content virality
    - Extracts topics, hashtags, formats
    - Identifies content gaps (opportunities)
    - Generates "steal the idea, do it better" briefs
    - Tracks follower growth trajectory
    - Alerts if competitor does something unusually successful
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.services.competitors.competitor_scraper import CompetitorScraper
    from app.services.competitors.competitor_analyzer import CompetitorAnalyzer
    import json
    
    log.info("agent.competitor_intelligence.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (4 hours TTL)
    cache_key = f"competitors_{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')}"
    cached = await cache.get_cached_result(
        agent_name="competitor_intelligence",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.competitor_intelligence.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["competitor_intelligence"] = cached
        state["active_agents"].append("competitor_intelligence")
        
        # Generate insights from cached data
        if cached.get("top_performing_content"):
            for content in cached["top_performing_content"][:3]:
                if content.get("virality_score", 0) > 80:
                    state["insights"].append({
                        "type": "competitor_move",
                        "priority": 8,
                        "title": f"🎯 Competitor viral content detected",
                        "body": content.get("steal_idea_brief", "High-performing content opportunity"),
                        "action": {"type": "create_content", "competitor_data": content},
                    })
        
        return state
    
    try:
        # Default competitors to track (can be customized per workspace)
        competitors_to_track = [
            {"platform": "instagram", "username": "techcreator"},
            {"platform": "youtube", "username": "contentpro"},
            {"platform": "tiktok", "username": "viralmaker"},
        ]
        
        log.info("agent.competitor_intelligence.scraping",
                workspace_id=state["workspace_id"],
                competitor_count=len(competitors_to_track))
        
        # Scrape competitors
        async with CompetitorScraper() as scraper:
            competitor_profiles = await scraper.scrape_multiple_competitors(
                competitors=competitors_to_track,
                max_content=10,
            )
        
        if not competitor_profiles:
            log.warning("agent.competitor_intelligence.no_data",
                       workspace_id=state["workspace_id"])
            
            empty_result = {
                "competitors_analyzed": 0,
                "message": "No competitor data available. Add competitors to track.",
                "provider": None,
                "model": None,
            }
            
            state["agent_results"]["competitor_intelligence"] = empty_result
            state["active_agents"].append("competitor_intelligence")
            
            return state
        
        # Analyze competitors
        analyzer = CompetitorAnalyzer()
        analyzed_profiles = []
        
        for profile in competitor_profiles:
            analysis = analyzer.analyze_competitor_profile(profile)
            analyzed_profiles.append(analysis)
        
        # Aggregate insights
        total_content = sum(p.get("content_analyzed", 0) for p in analyzed_profiles)
        avg_virality = sum(p.get("avg_virality_score", 0) for p in analyzed_profiles) / len(analyzed_profiles) if analyzed_profiles else 0
        
        # Collect top performing content across all competitors
        all_top_content = []
        for profile in analyzed_profiles:
            top_content = profile.get("top_performing_content", [])
            for content in top_content:
                content["competitor"] = profile.get("username")
                content["platform"] = profile.get("platform")
                all_top_content.append(content)
        
        # Sort by virality score
        all_top_content.sort(key=lambda x: x.get("virality_score", 0), reverse=True)
        
        # Identify content gaps (simplified - comparing topics)
        all_competitor_topics = []
        for profile in analyzed_profiles:
            for topic_data in profile.get("top_topics", []):
                all_competitor_topics.append(topic_data["topic"])
        
        # Count topic frequency
        topic_counts = {}
        for topic in all_competitor_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        content_gaps = [
            {
                "topic": topic,
                "frequency": count,
                "opportunity_score": min(count / len(analyzed_profiles) * 100, 100),
            }
            for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Use LLM to generate strategic insights
        provider, model = router.get_provider(TaskType.COMPETITOR_ANALYSIS)
        llm_client = get_llm_client()
        
        analysis_prompt = f"""You are a competitive intelligence analyst. Analyze these competitor insights and provide strategic recommendations.

Competitor Data:
- Competitors analyzed: {len(analyzed_profiles)}
- Total content analyzed: {total_content}
- Average virality score: {avg_virality:.1f}/100
- Top performing content: {json.dumps(all_top_content[:3], indent=2)}
- Content gaps: {json.dumps(content_gaps[:5], indent=2)}

Provide analysis in JSON format:
{{
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "competitive_advantages": ["what competitors do well"],
    "opportunities": ["gaps you can exploit"],
    "recommended_actions": ["specific action 1", "specific action 2"]
}}

Focus on:
1. What's working for competitors
2. Content gaps and opportunities
3. Actionable recommendations"""
        
        try:
            response = await llm_client.complete(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert competitive intelligence analyst who identifies content opportunities."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            # Parse LLM response
            try:
                strategic_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                strategic_analysis = {
                    "key_insights": ["Competitor analysis in progress"],
                    "competitive_advantages": ["Strong content performance"],
                    "opportunities": ["Multiple content gaps identified"],
                    "recommended_actions": ["Review top performing content"],
                }
            
            # Build result
            result = {
                "competitors_analyzed": len(analyzed_profiles),
                "total_content_analyzed": total_content,
                "avg_virality_score": round(avg_virality, 2),
                "top_performing_content": all_top_content[:10],
                "content_gaps": content_gaps,
                "strategic_analysis": strategic_analysis,
                "competitor_profiles": analyzed_profiles,
                "provider": provider,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Track usage
            await track_agent_step(
                "competitor_intelligence", state, db, provider, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 4 hours
            await cache.cache_result(
                agent_name="competitor_intelligence",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=14400,  # 4 hours
            )
            
            log.info("agent.competitor_intelligence.completed",
                     workspace_id=state["workspace_id"],
                     competitors_analyzed=len(analyzed_profiles),
                     content_gaps=len(content_gaps),
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.competitor_intelligence.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback without LLM analysis
            result = {
                "competitors_analyzed": len(analyzed_profiles),
                "total_content_analyzed": total_content,
                "avg_virality_score": round(avg_virality, 2),
                "top_performing_content": all_top_content[:10],
                "content_gaps": content_gaps,
                "strategic_analysis": {
                    "key_insights": [f"Analyzed {len(analyzed_profiles)} competitors"],
                    "opportunities": [f"Found {len(content_gaps)} content gaps"],
                },
                "competitor_profiles": analyzed_profiles,
                "provider": None,
                "model": None,
                "error": "LLM analysis unavailable, showing raw data",
            }
        
        state["agent_results"]["competitor_intelligence"] = result
        state["active_agents"].append("competitor_intelligence")
        
        # Generate insights for high-performing content
        for content in all_top_content[:5]:  # Top 5 only
            if content.get("virality_score", 0) > 80:
                state["insights"].append({
                    "type": "competitor_move",
                    "priority": 8,
                    "title": f"🎯 {content.get('competitor', 'Competitor')} viral content",
                    "body": content.get("steal_idea_brief", "High-performing content detected"),
                    "action": {"type": "create_content", "competitor_data": content},
                })
        
        # Generate insights for content gaps
        for gap in content_gaps[:3]:  # Top 3 gaps
            if gap.get("opportunity_score", 0) > 60:
                state["insights"].append({
                    "type": "content_gap",
                    "priority": 7,
                    "title": f"💡 Content gap: {gap['topic']}",
                    "body": f"Competitors are covering this heavily (opportunity score: {gap['opportunity_score']:.0f}/100). Consider creating content about this.",
                    "action": {"type": "create_content", "topic": gap["topic"]},
                })
    
    except Exception as e:
        log.error("agent.competitor_intelligence.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["competitor_intelligence"] = {
            "competitors_analyzed": 0,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("competitor_intelligence")
        state["errors"].append(f"competitor_intelligence: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 5: CONTENT RESEARCH & IDEATION AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def content_ideation_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Content Research & Ideation Agent - Never run out of content ideas.
    
    Runs: Daily (batch), On-demand
    
    Sources:
    - Niche news feeds (RSS, scraping)
    - Trending YouTube videos in niche
    - Reddit top posts (niche subreddits)
    - Twitter viral posts in niche
    - Google's "People Also Ask"
    - Answer The Public API
    - Product Hunt (tech)
    - ArXiv papers (science)
    
    Does:
    - Generates 5-10 content ideas per day
    - Each idea includes: title, hook, structure, hashtags, platform, virality estimate
    - Repurposing suggestions
    - Seasonal content calendar
    - Collaboration idea pairing
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, func, and_
    from app.domains.execution.models import ContentProject
    import json
    
    log.info("agent.content_ideation.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (6 hours TTL for content ideas)
    cache_key = f"ideas_{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')}"
    cached = await cache.get_cached_result(
        agent_name="content_ideation",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.content_ideation.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["content_ideation"] = cached
        state["active_agents"].append("content_ideation")
        state["content_ideas"].extend(cached.get("ideas", []))
        
        if cached.get("insights"):
            state["insights"].extend(cached["insights"])
        
        return state
    
    try:
        # Gather context from other agents
        trends = state["agent_results"].get("trend_detection", {}).get("trends", [])
        competitor_gaps = state["agent_results"].get("competitor_intelligence", {}).get("content_gaps", [])
        news_items = state["agent_results"].get("news_research", {}).get("news_items", [])
        
        # Query user's best performing content (last 90 days)
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        top_content_query = select(ContentProject).where(
            and_(
                ContentProject.workspace_id == workspace_id,
                ContentProject.created_at >= ninety_days_ago,
            )
        ).order_by(ContentProject.created_at.desc()).limit(10)
        
        result = await db.execute(top_content_query)
        top_content = result.scalars().all()
        
        # Prepare context for LLM
        content_history = []
        for content in top_content:
            content_history.append({
                "title": content.title or "Untitled",
                "status": content.status.value if hasattr(content.status, 'value') else str(content.status),
                "created_at": content.created_at.isoformat() if content.created_at else None,
            })
        
        # Use LLM to generate creative ideas
        provider, model = router.get_provider(TaskType.CREATIVE_WRITING)
        llm_client = get_llm_client()
        
        ideation_prompt = f"""You are a creative content strategist. Generate 5-7 fresh, viral-worthy content ideas for a creator.

Context:
- Recent trends: {json.dumps(trends[:3], indent=2) if trends else "No trend data available"}
- Competitor gaps: {json.dumps(competitor_gaps[:3], indent=2) if competitor_gaps else "No competitor data available"}
- Recent news: {json.dumps(news_items[:3], indent=2) if news_items else "No news data available"}
- Creator's recent content: {json.dumps(content_history[:5], indent=2) if content_history else "No content history"}

Generate ideas in JSON format:
{{
    "ideas": [
        {{
            "title": "compelling title that hooks attention",
            "hook": "first 3 seconds opening line",
            "content_type": "short_video|tutorial|carousel|thread|blog",
            "platforms": ["instagram", "tiktok", "youtube"],
            "hashtags": ["#relevant", "#hashtags"],
            "estimated_virality": 0.75,
            "rationale": "why this will work"
        }}
    ]
}}

Make ideas:
1. Timely (leverage trends if available)
2. Unique (different from recent content)
3. Actionable (creator can execute quickly)
4. Platform-appropriate
5. Viral-worthy (strong hooks, emotional resonance)"""
        
        try:
            response = await llm_client.complete(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert content strategist who generates viral-worthy content ideas. Be creative, specific, and actionable."},
                    {"role": "user", "content": ideation_prompt},
                ],
                temperature=0.9,  # Higher creativity
                max_tokens=1500,
            )
            
            # Parse LLM response
            try:
                ideation_result = json.loads(response.content)
                ideas = ideation_result.get("ideas", [])
            except json.JSONDecodeError:
                # Fallback if LLM doesn't return valid JSON
                ideas = [
                    {
                        "title": "Create content based on current trends",
                        "hook": "You won't believe what I just discovered...",
                        "content_type": "short_video",
                        "platforms": ["instagram", "tiktok"],
                        "hashtags": ["#trending", "#viral"],
                        "estimated_virality": 0.70,
                        "rationale": "Trending topics always perform well",
                    }
                ]
            
            # Calculate average virality
            avg_virality = sum(idea.get("estimated_virality", 0.5) for idea in ideas) / len(ideas) if ideas else 0.5
            
            # Build result
            result = {
                "ideas_generated": len(ideas),
                "avg_virality_score": round(avg_virality, 3),
                "ideas": ideas,
                "provider": provider,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Generate insight
            insights = []
            if ideas:
                top_idea = max(ideas, key=lambda x: x.get("estimated_virality", 0))
                insights.append({
                    "type": "content_idea",
                    "priority": 6,
                    "title": f"💡 {len(ideas)} fresh content ideas ready",
                    "body": f"Top idea: '{top_idea['title']}' (virality: {top_idea.get('estimated_virality', 0):.0%})",
                    "action": {"type": "view_ideas"},
                })
            
            result["insights"] = insights
            
            # Track usage
            await track_agent_step(
                "content_ideation", state, db, provider, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 6 hours
            await cache.cache_result(
                agent_name="content_ideation",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=21600,  # 6 hours
            )
            
            log.info("agent.content_ideation.completed",
                     workspace_id=state["workspace_id"],
                     ideas_generated=len(ideas),
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.content_ideation.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback to basic ideas without LLM
            ideas = [
                {
                    "title": "Share your creator journey",
                    "hook": "Here's what I learned this week...",
                    "content_type": "short_video",
                    "platforms": ["instagram", "tiktok"],
                    "hashtags": ["#creator", "#journey"],
                    "estimated_virality": 0.60,
                    "rationale": "Personal stories resonate with audiences",
                },
                {
                    "title": "Quick tips for your niche",
                    "hook": "3 things I wish I knew earlier...",
                    "content_type": "carousel",
                    "platforms": ["instagram", "linkedin"],
                    "hashtags": ["#tips", "#advice"],
                    "estimated_virality": 0.65,
                    "rationale": "Educational content performs consistently",
                },
            ]
            
            result = {
                "ideas_generated": len(ideas),
                "avg_virality_score": 0.625,
                "ideas": ideas,
                "provider": None,
                "model": None,
                "error": "LLM ideation unavailable, showing fallback ideas",
            }
            
            insights = [{
                "type": "content_idea",
                "priority": 6,
                "title": f"💡 {len(ideas)} content ideas ready",
                "body": "Basic content ideas available. Connect LLM for personalized suggestions.",
                "action": {"type": "view_ideas"},
            }]
            
            result["insights"] = insights
        
        state["agent_results"]["content_ideation"] = result
        state["active_agents"].append("content_ideation")
        state["content_ideas"].extend(ideas)
        state["insights"].extend(insights)
    
    except Exception as e:
        log.error("agent.content_ideation.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["content_ideation"] = {
            "ideas_generated": 0,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("content_ideation")
        state["errors"].append(f"content_ideation: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 6: GOAL & ACCOUNTABILITY AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def goal_accountability_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Goal & Accountability Agent - Digital coach that keeps creators on track.
    
    Runs: Daily check-in + event-triggered
    
    Does:
    - Monitors goal progress in real-time
    - Sends smart reminders (contextual, not annoying)
    - If behind: calculates catch-up plan
    - If ahead: celebrates and suggests stretch goals
    - Weekly goal review with AI commentary
    - Streak tracking and gamification
    - Sends push notifications
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, func, and_
    from app.domains.execution.models import CreatorGoal, ContentProject
    import json
    
    log.info("agent.goal_accountability.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (1 day TTL for goal checks)
    cache_key = f"goals_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    cached = await cache.get_cached_result(
        agent_name="goal_accountability",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.goal_accountability.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["goal_accountability"] = cached
        state["active_agents"].append("goal_accountability")
        
        if cached.get("insights"):
            state["insights"].extend(cached["insights"])
        
        return state
    
    try:
        # Query active goals
        goals_query = select(CreatorGoal).where(
            and_(
                CreatorGoal.workspace_id == workspace_id,
                CreatorGoal.status == "active",
            )
        )
        
        result = await db.execute(goals_query)
        goals = result.scalars().all()
        
        if not goals:
            log.info("agent.goal_accountability.no_goals", workspace_id=state["workspace_id"])
            
            empty_result = {
                "has_goals": False,
                "message": "No active goals set. Create goals to track your progress!",
                "provider": None,
                "model": None,
            }
            
            state["agent_results"]["goal_accountability"] = empty_result
            state["active_agents"].append("goal_accountability")
            
            # Suggest creating goals
            state["insights"].append({
                "type": "goal_suggestion",
                "priority": 6,
                "title": "🎯 Set your first goal",
                "body": "Track your progress and stay accountable. Start with a weekly posting goal!",
                "action": {"type": "create_goal"},
            })
            
            return state
        
        # Calculate progress for each goal
        goal_statuses = []
        behind_count = 0
        on_track_count = 0
        ahead_count = 0
        
        for goal in goals:
            # Calculate progress percentage
            if goal.target_value > 0:
                progress_pct = (goal.current_value / goal.target_value) * 100
            else:
                progress_pct = 0
            
            # Determine status
            if progress_pct < 50:
                status = "behind"
                behind_count += 1
            elif progress_pct < 90:
                status = "on_track"
                on_track_count += 1
            else:
                status = "ahead"
                ahead_count += 1
            
            goal_statuses.append({
                "id": str(goal.id),
                "title": goal.title,
                "goal_type": goal.goal_type,
                "period": goal.period,
                "target": float(goal.target_value),
                "current": float(goal.current_value),
                "progress_pct": round(progress_pct, 1),
                "status": status,
                "unit": goal.unit,
                "starts_at": goal.starts_at.isoformat() if goal.starts_at else None,
                "ends_at": goal.ends_at.isoformat() if goal.ends_at else None,
            })
        
        # Use LLM to generate personalized coaching
        provider, model = router.get_provider(TaskType.STRUCTURED_GENERATION)
        llm_client = get_llm_client()
        
        coaching_prompt = f"""You are a supportive creator coach. Analyze these goals and provide personalized, motivating feedback.

Goals Status:
{json.dumps(goal_statuses, indent=2)}

Provide coaching in JSON format:
{{
    "overall_assessment": "brief overall assessment",
    "motivational_message": "encouraging message",
    "action_items": ["specific action 1", "specific action 2"],
    "celebrations": ["achievement to celebrate"] or [],
    "warnings": ["concern to address"] or []
}}

Be specific, actionable, and encouraging. If behind, provide a realistic catch-up plan. If ahead, celebrate and suggest stretch goals."""
        
        try:
            response = await llm_client.complete(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert creator coach who provides supportive, actionable guidance."},
                    {"role": "user", "content": coaching_prompt},
                ],
                temperature=0.7,
                max_tokens=800,
            )
            
            # Parse LLM response
            try:
                coaching = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback if LLM doesn't return valid JSON
                coaching = {
                    "overall_assessment": "Keep pushing forward!",
                    "motivational_message": response.content[:200],
                    "action_items": ["Continue working on your goals"],
                    "celebrations": [],
                    "warnings": [],
                }
            
            # Build result
            result = {
                "has_goals": True,
                "goals_tracked": len(goals),
                "behind_count": behind_count,
                "on_track_count": on_track_count,
                "ahead_count": ahead_count,
                "goal_statuses": goal_statuses,
                "coaching": coaching,
                "provider": provider,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Generate insights
            insights = []
            
            # Add celebration insights
            for celebration in coaching.get("celebrations", []):
                insights.append({
                    "type": "goal_celebration",
                    "priority": 7,
                    "title": "🎉 Goal Achievement!",
                    "body": celebration,
                    "action": {"type": "view_goals"},
                })
            
            # Add warning insights
            for warning in coaching.get("warnings", []):
                insights.append({
                    "type": "goal_warning",
                    "priority": 8,
                    "title": "⚠️ Goal Alert",
                    "body": warning,
                    "action": {"type": "view_goals"},
                })
            
            # Add general reminder if behind on any goal
            if behind_count > 0:
                insights.append({
                    "type": "goal_reminder",
                    "priority": 8,
                    "title": f"⏰ {behind_count} goal{'s' if behind_count > 1 else ''} need attention",
                    "body": coaching.get("motivational_message", "Let's get back on track!"),
                    "action": {"type": "view_goals"},
                })
            
            # Add celebration if all goals on track or ahead
            if behind_count == 0 and len(goals) > 0:
                insights.append({
                    "type": "goal_success",
                    "priority": 7,
                    "title": "✅ All goals on track!",
                    "body": coaching.get("motivational_message", "You're crushing it! Keep going!"),
                    "action": {"type": "view_goals"},
                })
            
            result["insights"] = insights
            
            # Track usage
            await track_agent_step(
                "goal_accountability", state, db, provider, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 1 day
            await cache.cache_result(
                agent_name="goal_accountability",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=86400,  # 24 hours
            )
            
            log.info("agent.goal_accountability.completed",
                     workspace_id=state["workspace_id"],
                     goals_tracked=len(goals),
                     insights_count=len(insights),
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.goal_accountability.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback to basic analysis without LLM
            result = {
                "has_goals": True,
                "goals_tracked": len(goals),
                "behind_count": behind_count,
                "on_track_count": on_track_count,
                "ahead_count": ahead_count,
                "goal_statuses": goal_statuses,
                "coaching": {
                    "overall_assessment": f"Tracking {len(goals)} goals",
                    "motivational_message": "Keep working towards your goals!",
                    "action_items": ["Check your goal progress regularly"],
                },
                "provider": None,
                "model": None,
                "error": "LLM coaching unavailable, showing basic status",
            }
            
            insights = []
            if behind_count > 0:
                insights.append({
                    "type": "goal_reminder",
                    "priority": 8,
                    "title": f"⏰ {behind_count} goal{'s' if behind_count > 1 else ''} need attention",
                    "body": "Check your goals and create an action plan.",
                    "action": {"type": "view_goals"},
                })
            
            result["insights"] = insights
        
        state["agent_results"]["goal_accountability"] = result
        state["active_agents"].append("goal_accountability")
        state["insights"].extend(insights)
    
    except Exception as e:
        log.error("agent.goal_accountability.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["goal_accountability"] = {
            "has_goals": False,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("goal_accountability")
        state["errors"].append(f"goal_accountability: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 7: APPROVAL GATE
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events("approval_gate")
async def approval_gate(state: AgentState, db: AsyncSession) -> AgentState:
    """Approval Gate - Checks if approval is needed for high-risk actions.
    
    Checks:
    - Budget limits
    - Approval policies
    - Cost thresholds
    - Workspace settings
    
    Decisions:
    - Auto-approve if within limits
    - Request approval if exceeds thresholds
    - Block if hard limits exceeded
    """
    log.info("agent.approval_gate.started", workspace_id=state["workspace_id"])
    
    # TODO: Implement actual approval logic
    # - Check budget policies
    # - Verify cost estimates
    # - Create approval requests if needed
    
    # Mock implementation - auto-approve for now
    state["approval_decisions"]["auto_publish"] = "approved"
    state["approval_decisions"]["high_cost_operation"] = "approved"
    
    log.info("agent.approval_gate.completed",
             workspace_id=state["workspace_id"],
             decisions=state["approval_decisions"])
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 8: NEWS & RESEARCH AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def news_research_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """News & Research Agent - Personalized intelligence briefing.
    
    Runs: Every hour
    
    Sources (niche-specific):
    - Tech: TechCrunch, Hacker News, Product Hunt, ArXiv, GitHub Trending
    - Fitness: PubMed, Men's Health, Examine.com, NSCA journals
    - Finance: Bloomberg, Reuters, CNBC, SEC filings
    - Gaming: IGN, Kotaku, Steam charts, Twitch trending
    - Food/Cooking: Bon Appétit, NYT Cooking, Serious Eats
    - Beauty: WWD, Allure, emerging brand launches
    - General: Google News RSS, Twitter/X curated lists
    
    Does:
    - Fetches and summarizes articles
    - Explains "why this matters for your content"
    - Generates content angle from each news item
    - Curated daily briefing
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.services.news.news_fetcher import NewsFetcher
    import json
    
    log.info("agent.news_research.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (1 hour TTL)
    cache_key = f"news_{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')}"
    cached = await cache.get_cached_result(
        agent_name="news_research",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.news_research.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["news_research"] = cached
        state["active_agents"].append("news_research")
        
        # Generate insights from cached data
        if cached.get("news_items"):
            for item in cached["news_items"][:5]:
                if item.get("relevance_score", 0) > 0.7:
                    state["insights"].append({
                        "type": "news_alert",
                        "priority": 7,
                        "title": f"📰 {item['title']}",
                        "body": item.get("content_angle", item.get("summary", "")),
                        "action": {"type": "read_article", "url": item.get("url", "")},
                    })
        
        return state
    
    try:
        # Get workspace to determine niche
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        # Default niche and keywords (can be customized per workspace)
        niche = "tech"  # Default to tech
        niche_keywords = ["AI", "content creation", "creator tools", "social media", "productivity"]
        
        # Initialize news fetcher
        fetcher = NewsFetcher()
        
        log.info("agent.news_research.fetching",
                workspace_id=state["workspace_id"],
                niche=niche,
                keywords=niche_keywords)
        
        # Fetch and score news
        articles = await fetcher.fetch_and_score_news(
            niche=niche,
            niche_keywords=niche_keywords,
            max_items=20,
            min_relevance=0.3,
        )
        
        if not articles:
            log.warning("agent.news_research.no_articles",
                       workspace_id=state["workspace_id"])
            
            empty_result = {
                "articles_fetched": 0,
                "message": "No relevant news found at this time. Check back in an hour.",
                "provider": None,
                "model": None,
            }
            
            state["agent_results"]["news_research"] = empty_result
            state["active_agents"].append("news_research")
            
            return state
        
        # Use LLM to generate content angles
        provider, model = router.get_provider(TaskType.SUMMARIZATION)
        llm_client = get_llm_client()
        
        # Take top 10 articles for LLM analysis
        top_articles = articles[:10]
        
        analysis_prompt = f"""You are a content strategist. Analyze these news articles and generate content angles for a creator.

Articles:
{json.dumps([{
    "title": a["title"],
    "description": a.get("description", ""),
    "source": a.get("source", ""),
    "relevance": a.get("relevance_score", 0)
} for a in top_articles], indent=2)}

For each article, provide:
1. Brief summary (1-2 sentences)
2. "Why this matters for your content" explanation
3. Specific content angle (what video/post to create)
4. Estimated engagement potential (0-1)

Return JSON:
{{
    "articles": [
        {{
            "title": "...",
            "summary": "...",
            "why_it_matters": "...",
            "content_angle": "...",
            "engagement_potential": 0.85
        }}
    ]
}}

Focus on:
- Timely, trending topics
- Actionable content ideas
- Creator-relevant angles"""
        
        try:
            response = await llm_client.complete(
                provider=provider,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert content strategist who identifies news-worthy content opportunities for creators."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Parse LLM response
            try:
                analysis = json.loads(response.content)
                analyzed_articles = analysis.get("articles", [])
                
                # Merge LLM analysis with fetched articles
                news_items = []
                for i, article in enumerate(top_articles):
                    analyzed = analyzed_articles[i] if i < len(analyzed_articles) else {}
                    
                    news_items.append({
                        "title": article["title"],
                        "source": article.get("source", "Unknown"),
                        "url": article.get("url", ""),
                        "author": article.get("author", "Unknown"),
                        "published_at": article.get("published_at"),
                        "summary": analyzed.get("summary", article.get("description", "")),
                        "why_it_matters": analyzed.get("why_it_matters", "Relevant to your niche"),
                        "content_angle": analyzed.get("content_angle", "Create content about this topic"),
                        "relevance_score": article.get("relevance_score", 0.5),
                        "engagement_potential": analyzed.get("engagement_potential", 0.6),
                    })
            
            except json.JSONDecodeError:
                log.warning("agent.news_research.llm_parse_failed",
                           workspace_id=state["workspace_id"])
                # Use articles without LLM enhancement
                news_items = []
                for article in top_articles:
                    news_items.append({
                        "title": article["title"],
                        "source": article.get("source", "Unknown"),
                        "url": article.get("url", ""),
                        "author": article.get("author", "Unknown"),
                        "published_at": article.get("published_at"),
                        "summary": article.get("description", ""),
                        "why_it_matters": "Relevant to your niche",
                        "content_angle": f"Create content about: {article['title']}",
                        "relevance_score": article.get("relevance_score", 0.5),
                        "engagement_potential": 0.6,
                    })
            
            # Calculate average relevance
            avg_relevance = sum(item["relevance_score"] for item in news_items) / len(news_items) if news_items else 0
            
            # Build result
            result = {
                "articles_fetched": len(articles),
                "analyzed_articles": len(news_items),
                "avg_relevance": round(avg_relevance, 3),
                "news_items": news_items,
                "provider": provider,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Track usage
            await track_agent_step(
                "news_research", state, db, provider, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 1 hour
            await cache.cache_result(
                agent_name="news_research",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=3600,  # 1 hour
            )
            
            log.info("agent.news_research.completed",
                     workspace_id=state["workspace_id"],
                     articles_fetched=len(articles),
                     analyzed=len(news_items),
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.news_research.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback without LLM analysis
            news_items = []
            for article in top_articles:
                news_items.append({
                    "title": article["title"],
                    "source": article.get("source", "Unknown"),
                    "url": article.get("url", ""),
                    "summary": article.get("description", ""),
                    "content_angle": f"Create content about: {article['title']}",
                    "relevance_score": article.get("relevance_score", 0.5),
                })
            
            avg_relevance = sum(item["relevance_score"] for item in news_items) / len(news_items) if news_items else 0
            
            result = {
                "articles_fetched": len(articles),
                "analyzed_articles": len(news_items),
                "avg_relevance": round(avg_relevance, 3),
                "news_items": news_items,
                "provider": None,
                "model": None,
                "error": "LLM analysis unavailable, showing raw articles",
            }
        
        state["agent_results"]["news_research"] = result
        state["active_agents"].append("news_research")
        
        # Generate insights for high-relevance news
        for item in news_items[:5]:  # Top 5 only
            if item.get("relevance_score", 0) > 0.7:
                state["insights"].append({
                    "type": "news_alert",
                    "priority": 7,
                    "title": f"📰 {item['title']}",
                    "body": f"{item.get('summary', '')}. Content angle: {item.get('content_angle', '')}",
                    "action": {"type": "read_article", "url": item.get("url", "")},
                })
    
    except Exception as e:
        log.error("agent.news_research.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["news_research"] = {
            "articles_fetched": 0,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("news_research")
        state["errors"].append(f"news_research: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 9: TIPS, TRICKS & PLATFORM ALGORITHM AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def tips_tricks_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Tips, Tricks & Platform Algorithm Agent - Stay ahead of algorithm changes.
    
    Runs: Weekly (deep dive), Real-time for algorithm changes
    
    Sources:
    - Platform official creator blogs
    - Creator economy newsletters (Dan Runcie, Jack Appleby)
    - YouTube Creator Academy
    - Social Media Examiner
    - Top creator Discord servers
    
    Does:
    - Tracks algorithm change announcements
    - Tests posting strategies
    - Suggests format changes
    - A/B test framework
    - Platform-specific growth hacks
    - Watch time optimization
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.services.tips.tips_provider import TipsProvider
    import json
    
    log.info("agent.tips_tricks.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()

    # Try cache first (1 week TTL for tips)
    cache_key = f"tips_{datetime.now(timezone.utc).strftime('%Y-%W')}"  # Weekly cache
    try:
        cached = await cache.get_cached_result(
            agent_name="tips_tricks",
            workspace_id=str(workspace_id),
            cache_key=cache_key,
        )
    except Exception as exc:
        log.warning("agent.tips_tricks.cache_get_failed", error=str(exc))
        state["agent_results"]["tips_tricks"] = {"error": f"cache_failure: {exc}"}
        state["active_agents"].append("tips_tricks")
        state["errors"].append({"agent": "tips_tricks", "error": str(exc)})
        return state

    if cached:
        log.info("agent.tips_tricks.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["tips_tricks"] = cached
        state["active_agents"].append("tips_tricks")
        
        # Generate insights from cached data
        if cached.get("tips"):
            for tip in cached["tips"][:3]:  # Top 3 tips
                if tip.get("impact_score", 0) > 0.80:
                    state["insights"].append({
                        "type": "growth_hack",
                        "priority": 6,
                        "title": f"💡 {tip['platforms'][0].title()}: {tip['title']}",
                        "body": f"{tip['explanation']}. Expected: {tip['expected_impact']}",
                        "action": {"type": "apply_tip", "tip_data": tip},
                    })
        
        return state
    
    try:
        # Get workspace to determine active platforms
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        # Default platforms (can be customized per workspace)
        active_platforms = ["instagram", "youtube", "tiktok", "twitter", "linkedin"]
        
        # Initialize tips provider
        provider = TipsProvider()
        
        log.info("agent.tips_tricks.fetching",
                workspace_id=state["workspace_id"],
                platforms=active_platforms)
        
        # Get top tips across all platforms
        top_tips = provider.get_top_tips(
            platforms=active_platforms,
            limit=15,
        )
        
        # Get recent tips (last 30 days)
        recent_tips = provider.get_recent_tips(
            days=30,
            platforms=active_platforms,
        )
        
        # Get tips by type
        algorithm_hacks = provider.get_tips_by_type(
            tip_type="algorithm_hack",
            platforms=active_platforms,
        )
        
        engagement_hacks = provider.get_tips_by_type(
            tip_type="engagement_hack",
            platforms=active_platforms,
        )
        
        if not top_tips:
            log.warning("agent.tips_tricks.no_tips",
                       workspace_id=state["workspace_id"])
            
            empty_result = {
                "tips_found": 0,
                "message": "No tips available for your platforms.",
                "provider": None,
                "model": None,
            }
            
            state["agent_results"]["tips_tricks"] = empty_result
            state["active_agents"].append("tips_tricks")
            
            return state
        
        # Use LLM to prioritize and personalize tips
        provider_name, model = router.get_provider(TaskType.STRUCTURED_GENERATION)
        llm_client = get_llm_client()
        
        analysis_prompt = f"""You are a social media growth strategist. Analyze these platform tips and provide personalized recommendations.

Top Tips:
{json.dumps(top_tips[:10], indent=2)}

Recent Algorithm Changes:
{json.dumps(recent_tips[:5], indent=2)}

Provide analysis in JSON format:
{{
    "priority_tips": [
        {{
            "tip_title": "...",
            "platform": "...",
            "why_prioritize": "...",
            "action_steps": ["step 1", "step 2"]
        }}
    ],
    "quick_wins": ["quick win 1", "quick win 2"],
    "long_term_strategies": ["strategy 1", "strategy 2"]
}}

Focus on:
1. Highest impact tips (confidence + expected impact)
2. Recent algorithm changes (last 30 days)
3. Actionable recommendations"""
        
        try:
            response = await llm_client.complete(
                provider=provider_name,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert social media growth strategist who provides actionable platform-specific advice."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )
            
            # Parse LLM response
            try:
                analysis = json.loads(response.content)
            except json.JSONDecodeError:
                log.warning("agent.tips_tricks.llm_parse_failed",
                           workspace_id=state["workspace_id"])
                analysis = {
                    "priority_tips": [],
                    "quick_wins": ["Review platform-specific tips"],
                    "long_term_strategies": ["Stay updated on algorithm changes"],
                }
            
            # Calculate summary stats
            avg_impact_score = sum(tip.get("impact_score", 0) for tip in top_tips) / len(top_tips) if top_tips else 0
            avg_confidence = sum(tip.get("confidence", 0) for tip in top_tips) / len(top_tips) if top_tips else 0
            
            # Build result
            result = {
                "tips_found": len(top_tips),
                "recent_tips_count": len(recent_tips),
                "algorithm_hacks_count": len(algorithm_hacks),
                "engagement_hacks_count": len(engagement_hacks),
                "platforms_covered": active_platforms,
                "avg_impact_score": round(avg_impact_score, 3),
                "avg_confidence": round(avg_confidence, 3),
                "tips": top_tips,
                "recent_tips": recent_tips[:5],
                "analysis": analysis,
                "provider": provider_name,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Track usage
            await track_agent_step(
                "tips_tricks", state, db, provider_name, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 1 week
            await cache.cache_result(
                agent_name="tips_tricks",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=604800,  # 1 week
            )
            
            log.info("agent.tips_tricks.completed",
                     workspace_id=state["workspace_id"],
                     tips_found=len(top_tips),
                     recent_tips=len(recent_tips),
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.tips_tricks.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback without LLM analysis
            avg_impact_score = sum(tip.get("impact_score", 0) for tip in top_tips) / len(top_tips) if top_tips else 0
            avg_confidence = sum(tip.get("confidence", 0) for tip in top_tips) / len(top_tips) if top_tips else 0
            
            result = {
                "tips_found": len(top_tips),
                "recent_tips_count": len(recent_tips),
                "algorithm_hacks_count": len(algorithm_hacks),
                "engagement_hacks_count": len(engagement_hacks),
                "platforms_covered": active_platforms,
                "avg_impact_score": round(avg_impact_score, 3),
                "avg_confidence": round(avg_confidence, 3),
                "tips": top_tips,
                "recent_tips": recent_tips[:5],
                "analysis": {
                    "quick_wins": ["Review the top tips for your platforms"],
                    "long_term_strategies": ["Monitor algorithm changes weekly"],
                },
                "provider": None,
                "model": None,
                "error": "LLM analysis unavailable, showing raw tips",
            }
        
        state["agent_results"]["tips_tricks"] = result
        state["active_agents"].append("tips_tricks")
        
        # Generate insights for high-impact tips
        for tip in top_tips[:5]:  # Top 5 only
            if tip.get("impact_score", 0) > 0.80:
                state["insights"].append({
                    "type": "growth_hack",
                    "priority": 6,
                    "title": f"💡 {tip['platforms'][0].title()}: {tip['title']}",
                    "body": f"{tip['explanation']}. Expected: {tip['expected_impact']}",
                    "action": {"type": "apply_tip", "tip_data": tip},
                })
        
        # Generate insight for recent algorithm changes
        if recent_tips:
            state["insights"].append({
                "type": "algorithm_update",
                "priority": 7,
                "title": f"🔔 {len(recent_tips)} recent algorithm updates",
                "body": f"New platform changes detected in the last 30 days. Review to stay ahead.",
                "action": {"type": "view_tips"},
            })
    
    except Exception as e:
        log.error("agent.tips_tricks.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["tips_tricks"] = {
            "tips_found": 0,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("tips_tricks")
        state["errors"].append(f"tips_tricks: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 10: SMART SCHEDULING AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def smart_scheduling_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Smart Scheduling Agent - Post at exactly the right time.
    
    Runs: Weekly recalculation + before each scheduled post
    
    Does:
    - Analyzes creator's audience activity patterns
    - Cross-references platform's peak traffic times
    - Considers competitor posting schedule
    - Timezone-aware for global audiences
    - Adjusts for content type
    - Handles queue management
    - Suggests frequency per platform
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.domains.execution.models import ContentProject
    from app.services.scheduling.schedule_optimizer import ScheduleOptimizer
    import json
    
    log.info("agent.smart_scheduling.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (1 week TTL for schedule optimization)
    cache_key = f"schedule_{datetime.now(timezone.utc).strftime('%Y-%W')}"  # Weekly cache
    cached = await cache.get_cached_result(
        agent_name="smart_scheduling",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.smart_scheduling.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["smart_scheduling"] = cached
        state["active_agents"].append("smart_scheduling")
        
        # Generate insights from cached data
        if cached.get("optimal_schedules"):
            for platform, schedule in list(cached["optimal_schedules"].items())[:2]:
                state["insights"].append({
                    "type": "scheduling_recommendation",
                    "priority": 5,
                    "title": f"⏰ {platform.title()}: Optimal posting times",
                    "body": f"{schedule['reasoning']}. Post {schedule['recommended_frequency']['posts_per_week']}x/week.",
                    "action": {"type": "update_schedule", "schedule_data": schedule},
                })
        
        return state
    
    try:
        # Get workspace
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        # Get content history (last 90 days) for audience activity analysis
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        content_query = select(ContentProject).where(
            ContentProject.workspace_id == workspace_id,
            ContentProject.created_at >= ninety_days_ago,
        ).order_by(ContentProject.created_at.desc()).limit(100)
        
        content_result = await db.execute(content_query)
        content_items = content_result.scalars().all()
        
        # Convert to dict format for optimizer
        content_history = []
        for item in content_items:
            content_history.append({
                "published_at": item.created_at,
                "views": 0,  # TODO: Get from analytics
                "likes": 0,
                "comments": 0,
                "shares": 0,
            })
        
        # Initialize optimizer
        optimizer = ScheduleOptimizer()
        
        log.info("agent.smart_scheduling.analyzing",
                workspace_id=state["workspace_id"],
                content_count=len(content_history))
        
        # Analyze audience activity
        audience_activity = optimizer.analyze_audience_activity(content_history)
        
        # Default platforms (can be customized per workspace)
        active_platforms = ["instagram", "youtube", "tiktok", "twitter", "linkedin"]
        
        # Calculate optimal schedules for each platform
        optimal_schedules = {}
        for platform in active_platforms:
            schedule = optimizer.calculate_optimal_schedule(
                platform=platform,
                audience_activity=audience_activity,
                timezone="UTC",  # TODO: Get from workspace settings
            )
            optimal_schedules[platform] = schedule
        
        # Generate weekly schedule
        weekly_schedule = optimizer.generate_weekly_schedule(
            platforms=active_platforms,
            audience_activity=audience_activity,
            timezone="UTC",
        )
        
        # Use LLM to generate personalized scheduling recommendations
        provider_name, model = router.get_provider(TaskType.STRUCTURED_GENERATION)
        llm_client = get_llm_client()
        
        analysis_prompt = f"""You are a social media scheduling expert. Analyze these optimal posting times and provide personalized recommendations.

Audience Activity Analysis:
- Peak hours: {audience_activity.get('peak_hours', [])}
- Peak days: {audience_activity.get('peak_days', [])}
- Content analyzed: {audience_activity.get('total_content_analyzed', 0)}

Optimal Schedules:
{json.dumps({k: {
    'best_days': v['best_days'],
    'best_times': v['best_times'],
    'posts_per_week': v['recommended_frequency']['posts_per_week']
} for k, v in optimal_schedules.items()}, indent=2)}

Provide analysis in JSON format:
{{
    "key_insights": ["insight 1", "insight 2"],
    "scheduling_tips": ["tip 1", "tip 2"],
    "platform_priorities": ["which platform to focus on first"],
    "consistency_advice": "advice on maintaining posting consistency"
}}

Focus on:
1. Most impactful posting times
2. Realistic posting frequency
3. Platform-specific strategies"""
        
        try:
            response = await llm_client.complete(
                provider=provider_name,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert social media scheduling strategist who helps creators optimize their posting times."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            # Parse LLM response
            try:
                llm_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                log.warning("agent.smart_scheduling.llm_parse_failed",
                           workspace_id=state["workspace_id"])
                llm_analysis = {
                    "key_insights": ["Optimal posting times calculated"],
                    "scheduling_tips": ["Post consistently at recommended times"],
                    "platform_priorities": ["Focus on your top platforms"],
                    "consistency_advice": "Consistency is key to growth",
                }
            
            # Build result
            result = {
                "has_data": True,
                "content_analyzed": len(content_history),
                "platforms_analyzed": len(active_platforms),
                "audience_activity": audience_activity,
                "optimal_schedules": optimal_schedules,
                "weekly_schedule": weekly_schedule,
                "llm_analysis": llm_analysis,
                "provider": provider_name,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Track usage
            await track_agent_step(
                "smart_scheduling", state, db, provider_name, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 1 week
            await cache.cache_result(
                agent_name="smart_scheduling",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=604800,  # 1 week
            )
            
            log.info("agent.smart_scheduling.completed",
                     workspace_id=state["workspace_id"],
                     platforms_analyzed=len(active_platforms),
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.smart_scheduling.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback without LLM analysis
            result = {
                "has_data": True,
                "content_analyzed": len(content_history),
                "platforms_analyzed": len(active_platforms),
                "audience_activity": audience_activity,
                "optimal_schedules": optimal_schedules,
                "weekly_schedule": weekly_schedule,
                "llm_analysis": {
                    "key_insights": [f"Analyzed {len(active_platforms)} platforms"],
                    "scheduling_tips": ["Follow the recommended posting times"],
                },
                "provider": None,
                "model": None,
                "error": "LLM analysis unavailable, showing calculated schedules",
            }
        
        state["agent_results"]["smart_scheduling"] = result
        state["active_agents"].append("smart_scheduling")
        
        # Generate insights for top 2 platforms
        for platform, schedule in list(optimal_schedules.items())[:2]:
            state["insights"].append({
                "type": "scheduling_recommendation",
                "priority": 5,
                "title": f"⏰ {platform.title()}: Optimal posting times",
                "body": f"{schedule['reasoning']}. Post {schedule['recommended_frequency']['posts_per_week']}x/week on {', '.join(schedule['best_days'][:2])} at {', '.join(schedule['best_times'][:2])}.",
                "action": {"type": "update_schedule", "schedule_data": schedule},
            })
    
    except Exception as e:
        log.error("agent.smart_scheduling.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["smart_scheduling"] = {
            "has_data": False,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("smart_scheduling")
        state["errors"].append(f"smart_scheduling: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 11: GROWTH & ENGAGEMENT OPTIMIZATION AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def growth_optimization_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Growth & Engagement Optimization Agent - Maximize reach and followers.
    
    Runs: Daily analysis + post-publish
    
    Does:
    - Hashtag strategy optimization
    - Comment engagement timing
    - Suggests which comments to reply to
    - Caption optimization for SEO
    - Cross-platform promotion strategy
    - Thumbnail/cover image A/B testing
    - CTA optimization
    - Collab/duet strategy
    - Viral loop detection
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.domains.execution.models import ContentProject
    from app.services.growth.growth_optimizer import GrowthOptimizer
    import json
    
    log.info("agent.growth_optimization.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    cache = get_cache_manager()
    
    # Try cache first (1 day TTL for growth analysis)
    cache_key = f"growth_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    cached = await cache.get_cached_result(
        agent_name="growth_optimization",
        workspace_id=str(workspace_id),
        cache_key=cache_key,
    )
    
    if cached:
        log.info("agent.growth_optimization.cache_hit", workspace_id=state["workspace_id"])
        state["agent_results"]["growth_optimization"] = cached
        state["active_agents"].append("growth_optimization")
        
        # Generate insights from cached data
        if cached.get("optimizations"):
            for opt in cached["optimizations"][:3]:
                if opt.get("confidence", 0) > 0.80:
                    state["insights"].append({
                        "type": "growth_opportunity",
                        "priority": 8,
                        "title": f"📈 {opt['type'].replace('_', ' ').title()}",
                        "body": f"{opt['recommendation']}. Expected: {opt['expected_impact']}",
                        "action": {"type": "apply_optimization", "optimization_data": opt},
                    })
        
        return state
    
    try:
        # Get workspace
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        # Get content history (last 90 days) for analysis
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        content_query = select(ContentProject).where(
            ContentProject.workspace_id == workspace_id,
            ContentProject.created_at >= ninety_days_ago,
        ).order_by(ContentProject.created_at.desc()).limit(100)
        
        content_result = await db.execute(content_query)
        content_items = content_result.scalars().all()
        
        if not content_items:
            log.info("agent.growth_optimization.no_data", workspace_id=state["workspace_id"])
            
            empty_result = {
                "has_data": False,
                "message": "No content data available yet. Start creating content to analyze growth opportunities!",
                "provider": None,
                "model": None,
            }
            
            state["agent_results"]["growth_optimization"] = empty_result
            state["active_agents"].append("growth_optimization")
            
            return state
        
        # Convert to dict format for optimizer
        content_data = []
        for item in content_items:
            content_data.append({
                "title": item.title or "Untitled",
                "caption": "",  # TODO: Get from content metadata
                "hashtags": [],  # TODO: Extract from content
                "content_type": "post",  # TODO: Get from content
                "views": 0,  # TODO: Get from analytics
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "saves": 0,
            })
        
        # Initialize optimizer
        optimizer = GrowthOptimizer()
        
        log.info("agent.growth_optimization.analyzing",
                workspace_id=state["workspace_id"],
                content_count=len(content_data))
        
        # Analyze hashtag performance
        hashtag_analysis = optimizer.analyze_hashtag_performance(content_data)
        
        # Analyze comment engagement
        comment_analysis = optimizer.analyze_comment_engagement(content_data)
        
        # Analyze CTA effectiveness
        cta_analysis = optimizer.analyze_cta_effectiveness(content_data)
        
        # Detect viral loops
        viral_analysis = optimizer.detect_viral_loops(content_data)
        
        # Calculate overall growth score
        growth_score = optimizer.calculate_growth_score(
            hashtag_analysis,
            comment_analysis,
            cta_analysis,
            viral_analysis,
        )
        
        # Compile all optimizations
        all_optimizations = []
        
        # Add hashtag optimizations
        for rec in hashtag_analysis.get("recommendations", [])[:2]:
            all_optimizations.append({
                "type": "hashtag_strategy",
                "recommendation": rec,
                "expected_impact": "+30-50% reach",
                "confidence": 0.85,
            })
        
        # Add comment optimizations
        for rec in comment_analysis.get("recommendations", [])[:2]:
            all_optimizations.append({
                "type": "comment_engagement",
                "recommendation": rec,
                "expected_impact": "+20-35% comments",
                "confidence": 0.88,
            })
        
        # Add CTA optimizations
        for rec in cta_analysis.get("recommendations", [])[:2]:
            all_optimizations.append({
                "type": "cta_optimization",
                "recommendation": rec,
                "expected_impact": "+25-40% conversions",
                "confidence": 0.82,
            })
        
        # Add viral optimizations
        for rec in viral_analysis.get("recommendations", [])[:2]:
            all_optimizations.append({
                "type": "viral_strategy",
                "recommendation": rec,
                "expected_impact": "+50-100% shares",
                "confidence": 0.75,
            })
        
        # Use LLM to prioritize and personalize optimizations
        provider_name, model = router.get_provider(TaskType.STRUCTURED_GENERATION)
        llm_client = get_llm_client()
        
        analysis_prompt = f"""You are a growth optimization expert. Analyze these optimization opportunities and provide prioritized recommendations.

Growth Score: {growth_score['overall_score']}/100 (Grade: {growth_score['grade']})
Score Breakdown:
- Hashtag Strategy: {growth_score['score_breakdown']['hashtag_strategy']}/100
- Comment Engagement: {growth_score['score_breakdown']['comment_engagement']}/100
- CTA Effectiveness: {growth_score['score_breakdown']['cta_effectiveness']}/100
- Viral Potential: {growth_score['score_breakdown']['viral_potential']}/100

Top Strength: {growth_score['top_strength']}
Top Weakness: {growth_score['top_weakness']}

Optimization Opportunities:
{json.dumps(all_optimizations[:8], indent=2)}

Provide analysis in JSON format:
{{
    "priority_optimizations": [
        {{
            "optimization": "specific action to take",
            "why_prioritize": "reason this is high priority",
            "quick_win": true/false
        }}
    ],
    "growth_strategy": "overall strategy recommendation",
    "expected_timeline": "how long to see results"
}}

Focus on:
1. Highest impact optimizations
2. Quick wins (easy to implement)
3. Addressing the top weakness"""
        
        try:
            response = await llm_client.complete(
                provider=provider_name,
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert growth strategist who helps creators maximize their reach and engagement."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=1200,
            )
            
            # Parse LLM response
            try:
                llm_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                log.warning("agent.growth_optimization.llm_parse_failed",
                           workspace_id=state["workspace_id"])
                llm_analysis = {
                    "priority_optimizations": [],
                    "growth_strategy": "Focus on improving your weakest areas",
                    "expected_timeline": "2-4 weeks",
                }
            
            # Build result
            result = {
                "has_data": True,
                "content_analyzed": len(content_data),
                "growth_score": growth_score,
                "hashtag_analysis": hashtag_analysis,
                "comment_analysis": comment_analysis,
                "cta_analysis": cta_analysis,
                "viral_analysis": viral_analysis,
                "optimizations": all_optimizations,
                "llm_analysis": llm_analysis,
                "provider": provider_name,
                "model": model,
                "tokens_used": response.tokens_in + response.tokens_out,
                "cost_usd": response.cost_usd,
            }
            
            # Track usage
            await track_agent_step(
                "growth_optimization", state, db, provider_name, model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
            
            # Cache result for 1 day
            await cache.cache_result(
                agent_name="growth_optimization",
                workspace_id=str(workspace_id),
                cache_key=cache_key,
                result=result,
                ttl=86400,  # 1 day
            )
            
            log.info("agent.growth_optimization.completed",
                     workspace_id=state["workspace_id"],
                     optimizations_found=len(all_optimizations),
                     growth_score=growth_score["overall_score"],
                     cost_usd=response.cost_usd)
        
        except Exception as llm_error:
            log.error("agent.growth_optimization.llm_failed",
                      workspace_id=state["workspace_id"],
                      error=str(llm_error))
            
            # Fallback without LLM analysis
            result = {
                "has_data": True,
                "content_analyzed": len(content_data),
                "growth_score": growth_score,
                "hashtag_analysis": hashtag_analysis,
                "comment_analysis": comment_analysis,
                "cta_analysis": cta_analysis,
                "viral_analysis": viral_analysis,
                "optimizations": all_optimizations,
                "llm_analysis": {
                    "growth_strategy": f"Focus on improving {growth_score['top_weakness']}",
                    "expected_timeline": "2-4 weeks",
                },
                "provider": None,
                "model": None,
                "error": "LLM analysis unavailable, showing calculated optimizations",
            }
        
        state["agent_results"]["growth_optimization"] = result
        state["active_agents"].append("growth_optimization")
        
        # Generate insights for high-confidence optimizations
        for opt in all_optimizations[:5]:  # Top 5 only
            if opt.get("confidence", 0) > 0.80:
                state["insights"].append({
                    "type": "growth_opportunity",
                    "priority": 8,
                    "title": f"📈 {opt['type'].replace('_', ' ').title()}",
                    "body": f"{opt['recommendation']}. Expected: {opt['expected_impact']}",
                    "action": {"type": "apply_optimization", "optimization_data": opt},
                })
        
        # Generate insight for overall growth score
        if growth_score["overall_score"] < 60:
            state["insights"].append({
                "type": "growth_alert",
                "priority": 9,
                "title": f"⚠️ Growth Score: {growth_score['overall_score']}/100 (Grade {growth_score['grade']})",
                "body": f"Focus on improving {growth_score['top_weakness']}. {len(all_optimizations)} optimization opportunities found.",
                "action": {"type": "view_growth_analysis"},
            })
        elif growth_score["overall_score"] >= 80:
            state["insights"].append({
                "type": "growth_success",
                "priority": 6,
                "title": f"🎉 Excellent Growth Score: {growth_score['overall_score']}/100 (Grade {growth_score['grade']})",
                "body": f"Your {growth_score['top_strength']} is strong! Keep it up.",
                "action": {"type": "view_growth_analysis"},
            })
    
    except Exception as e:
        log.error("agent.growth_optimization.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["growth_optimization"] = {
            "has_data": False,
            "error": str(e),
            "provider": None,
            "model": None,
        }
        state["active_agents"].append("growth_optimization")
        state["errors"].append(f"growth_optimization: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 12: VIDEO INTELLIGENCE AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def video_intelligence_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Video Intelligence Agent - Make every video better before publishing.
    
    Runs: On-demand (when video is uploaded)
    
    Does:
    - Hook effectiveness scoring
    - Pacing analysis (filler words, speaking pace)
    - Platform fit analysis
    - Clip suggestions for short-form
    - Caption suggestions
    - Quality scoring
    - Improvement recommendations
    """
    log.info("agent.video_intelligence.started", workspace_id=state["workspace_id"])
    
    from app.services.video import VideoAnalyzer
    
    analyzer = VideoAnalyzer()
    
    # Get recent videos from database
    from app.models.models import ContentItem
    from sqlalchemy import select
    
    result = await db.execute(
        select(ContentItem)
        .where(ContentItem.workspace_id == state["workspace_id"])
        .where(ContentItem.content_type.in_(["reel", "short", "video"]))
        .where(ContentItem.video_url.isnot(None))
        .order_by(ContentItem.created_at.desc())
        .limit(5)
    )
    videos = result.scalars().all()
    
    if not videos:
        log.info("agent.video_intelligence.no_videos", workspace_id=state["workspace_id"])
        state["agent_results"]["video_intelligence"] = {
            "videos_analyzed": 0,
            "message": "No videos found to analyze",
        }
        state["active_agents"].append("video_intelligence")
        return state
    
    # Analyze each video
    analyses = []
    for video in videos:
        analysis = analyzer.analyze_video(
            video_url=video.video_url,
            transcript=video.script,  # Use script as transcript
            duration_seconds=video.video_duration,
            thumbnail_url=video.thumbnail_url,
        )
        
        # Add video metadata
        analysis["video_id"] = str(video.id)
        analysis["title"] = video.title
        
        # Generate clip suggestions if transcript available
        if video.script and video.video_duration:
            clips = analyzer.suggest_clips(
                transcript=video.script,
                duration_seconds=video.video_duration,
                target_duration=30,
            )
            analysis["suggested_clips"] = clips
        
        # Generate caption suggestions
        if video.script:
            captions = analyzer.generate_caption_suggestions(
                transcript=video.script,
                platform="instagram",
            )
            analysis["caption_suggestions"] = captions
        
        analyses.append(analysis)
    
    # Find best and worst performing videos
    analyses_sorted = sorted(analyses, key=lambda x: x.get("quality_score", 0), reverse=True)
    best_video = analyses_sorted[0] if analyses_sorted else None
    worst_video = analyses_sorted[-1] if len(analyses_sorted) > 1 else None
    
    state["agent_results"]["video_intelligence"] = {
        "videos_analyzed": len(analyses),
        "analyses": analyses,
        "best_video": best_video,
        "worst_video": worst_video,
        "avg_quality_score": sum(a.get("quality_score", 0) for a in analyses) / len(analyses) if analyses else 0,
    }
    state["active_agents"].append("video_intelligence")
    
    # Generate insights
    if best_video:
        quality = best_video.get("quality_score", 0)
        recommendations = best_video.get("recommendations", [])
        
        if quality >= 0.8:
            state["insights"].append({
                "type": "video_excellence",
                "priority": 8,
                "title": f"🎬 Excellent video quality: {best_video.get('title', 'Untitled')}",
                "body": f"Quality score: {quality:.0%}. This video has strong hooks and great pacing. Ready to publish!",
                "action": {"type": "view_video", "video_id": best_video.get("video_id")},
            })
        elif recommendations:
            state["insights"].append({
                "type": "video_optimization",
                "priority": 7,
                "title": f"🎬 Video improvements suggested: {best_video.get('title', 'Untitled')}",
                "body": f"Quality score: {quality:.0%}. {recommendations[0]}",
                "action": {"type": "view_video", "video_id": best_video.get("video_id")},
            })
    
    # No LLM calls - pure algorithmic analysis
    await track_agent_step(
        "video_intelligence", state, db, "none", "algorithmic",
        tokens_in=0, tokens_out=0
    )
    
    log.info("agent.video_intelligence.completed", 
             workspace_id=state["workspace_id"],
             videos_analyzed=len(analyses))
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 13: PREDICTIVE VIRALITY AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def predictive_virality_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Predictive Virality Agent - Predict performance BEFORE posting.
    
    Runs: On-demand pre-publish
    
    Scores content on 12 virality signals:
    1. Hook strength (first 3 seconds)
    2. Emotional resonance
    3. Shareability factor
    4. Trend alignment
    5. Caption engagement potential
    6. Hashtag reach
    7. Platform fit
    8. Posting time alignment
    9. Content uniqueness
    10. CTA strength
    11. Visual quality estimate
    12. Audio quality estimate
    
    Does:
    - Scores each signal 0-1
    - Explains what to improve
    - Simulates likely outcome range
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.domains.execution.models import ContentProject
    from app.services.virality.virality_predictor import ViralityPredictor
    import json
    
    log.info("agent.predictive_virality.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    
    try:
        # Get content to analyze (from state or latest draft)
        content_to_analyze = state.get("content_to_analyze")
        
        if not content_to_analyze:
            # Get latest draft content
            content_query = select(ContentProject).where(
                ContentProject.workspace_id == workspace_id,
                ContentProject.status == "draft",
            ).order_by(ContentProject.created_at.desc()).limit(1)
            
            content_result = await db.execute(content_query)
            content_item = content_result.scalar_one_or_none()
            
            if not content_item:
                log.info("agent.predictive_virality.no_content", workspace_id=state["workspace_id"])
                
                empty_result = {
                    "has_content": False,
                    "message": "No content to analyze. Create a draft to predict its virality!",
                }
                
                state["agent_results"]["predictive_virality"] = empty_result
                state["active_agents"].append("predictive_virality")
                
                return state
            
            content_to_analyze = {
                "title": content_item.title or "",
                "caption": "",  # TODO: Get from metadata
                "hashtags": [],  # TODO: Extract from content
                "content_type": "post",
                "scheduled_at": None,
                "has_thumbnail": False,
                "media_count": 0,
                "has_audio": False,
            }
        
        # Get historical performance for this creator
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        history_query = select(ContentProject).where(
            ContentProject.workspace_id == workspace_id,
            ContentProject.created_at >= ninety_days_ago,
        ).order_by(ContentProject.created_at.desc()).limit(50)
        
        history_result = await db.execute(history_query)
        history_items = history_result.scalars().all()
        
        # Build historical performance data
        historical_performance = None
        if history_items:
            past_titles = [item.title for item in history_items if item.title]
            historical_performance = {
                "past_titles": past_titles,
                "avg_views": 1000,  # TODO: Calculate from analytics
                "avg_engagement_rate": 0.05,  # TODO: Calculate from analytics
            }
        
        # Get trending topics from trend agent
        trending_topics = []
        if "trend_detection" in state["agent_results"]:
            trends = state["agent_results"]["trend_detection"].get("trends", [])
            trending_topics = [t.get("title", "") for t in trends[:10]]
        
        # Initialize predictor
        predictor = ViralityPredictor()
        
        # Default platform
        platform = "instagram"  # TODO: Get from content or workspace settings
        
        log.info("agent.predictive_virality.analyzing",
                workspace_id=state["workspace_id"],
                platform=platform)
        
        # Predict virality
        prediction = predictor.predict_virality(
            content=content_to_analyze,
            platform=platform,
            historical_performance=historical_performance,
            trending_topics=trending_topics,
        )
        
        # Build result
        result = {
            "has_content": True,
            "platform": platform,
            "overall_score": prediction["overall_score"],
            "grade": prediction["grade"],
            "signals": prediction["signals"],
            "top_strengths": prediction["top_strengths"],
            "top_weaknesses": prediction["top_weaknesses"],
            "improvements": prediction["improvements"],
            "predicted_range": prediction["predicted_range"],
            "confidence": prediction["confidence"],
        }
        
        state["agent_results"]["predictive_virality"] = result
        state["active_agents"].append("predictive_virality")
        
        # Generate insight
        score_pct = int(prediction["overall_score"] * 100)
        predicted_views = prediction["predicted_range"]["views_likely"]
        predicted_engagement = prediction["predicted_range"]["engagement_rate"]
        
        if prediction["overall_score"] >= 0.80:
            priority = 9
            emoji = "🚀"
            message = f"Excellent virality potential! Predicted: {predicted_views:,} views, {predicted_engagement:.1%} engagement."
        elif prediction["overall_score"] >= 0.65:
            priority = 7
            emoji = "✅"
            message = f"Good virality potential. Predicted: {predicted_views:,} views, {predicted_engagement:.1%} engagement."
        else:
            priority = 8
            emoji = "⚠️"
            message = f"Moderate virality potential. Predicted: {predicted_views:,} views. Consider improvements."
        
        state["insights"].append({
            "type": "virality_prediction",
            "priority": priority,
            "title": f"{emoji} Virality Score: {score_pct}% (Grade {prediction['grade']})",
            "body": f"{message} Top improvement: {prediction['improvements'][0] if prediction['improvements'] else 'Content looks good!'}",
            "action": {"type": "view_prediction", "prediction_data": prediction},
        })
        
        log.info("agent.predictive_virality.completed",
                 workspace_id=state["workspace_id"],
                 overall_score=prediction["overall_score"],
                 grade=prediction["grade"])
    
    except Exception as e:
        log.error("agent.predictive_virality.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["predictive_virality"] = {
            "has_content": False,
            "error": str(e),
        }
        state["active_agents"].append("predictive_virality")
        state["errors"].append(f"predictive_virality: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 14: COLLABORATION & BUSINESS AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@with_node_events()
async def collaboration_business_agent(state: AgentState, db: AsyncSession) -> AgentState:
    """Collaboration & Business Agent - Automate the business side of creating.
    
    Runs: Continuously (webhook-driven for DMs) + Daily
    
    Does:
    - Monitors DM inboxes across all platforms
    - AI classifies incoming DMs (brand deal / collab / fan / spam)
    - Scores deal quality
    - Drafts personalized reply suggestions
    - Tracks deal pipeline
    - Generates contract drafts
    - Flags suspicious deals
    - Sends invoice reminders
    - Suggests outreach targets
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.domains.control.models import Workspace
    from app.services.collaboration.dm_classifier import DMClassifier
    from app.services.collaboration.deal_tracker import DealTracker
    import json
    
    log.info("agent.collaboration_business.started", workspace_id=state["workspace_id"])
    
    workspace_id = uuid.UUID(state["workspace_id"])
    
    try:
        # Get workspace
        workspace_query = select(Workspace).where(Workspace.id == workspace_id)
        workspace_result = await db.execute(workspace_query)
        workspace = workspace_result.scalar_one_or_none()
        
        # Mock DM data (in production, fetch from connected platforms)
        mock_dms = [
            {
                "id": "dm1",
                "sender": "TechBrand",
                "text": "Hi! We'd love to partner with you for our new product launch. We have a budget of $5000 for a sponsored post. Interested?",
                "sender_followers": 50000,
                "sender_verified": True,
            },
            {
                "id": "dm2",
                "sender": "CreatorFriend",
                "text": "Hey! Want to collab on a video together? I think our audiences would love it!",
                "sender_followers": 25000,
                "sender_verified": False,
            },
            {
                "id": "dm3",
                "sender": "Fan123",
                "text": "Love your content! You inspire me every day. Keep it up!",
                "sender_followers": 500,
                "sender_verified": False,
            },
            {
                "id": "dm4",
                "sender": "SpamBot",
                "text": "Click here to make money fast! Limited time offer!",
                "sender_followers": 10,
                "sender_verified": False,
            },
        ]
        
        # Initialize classifier and tracker
        classifier = DMClassifier()
        tracker = DealTracker()
        
        log.info("agent.collaboration_business.classifying",
                workspace_id=state["workspace_id"],
                dm_count=len(mock_dms))
        
        # Classify all DMs
        classified_dms = classifier.batch_classify(mock_dms)
        
        # Get business inquiries
        business_inquiries = classifier.get_business_inquiries(classified_dms)
        
        # Score deals
        scored_deals = []
        for inquiry in business_inquiries:
            if inquiry["category"] == "brand_deal":
                # Extract deal info (simplified)
                deal_info = {
                    "brand_name": inquiry["sender"],
                    "offered_amount": 5000,  # TODO: Extract from message
                    "brand_followers": inquiry.get("sender_followers", 0),
                    "brand_verified": False,
                    "creator_followers": 10000,  # TODO: Get from workspace
                    "niche_match": 0.8,
                    "deliverables": ["1 post"],
                    "deadline_days": 30,
                    "description": inquiry.get("text", ""),
                    "terms": "",
                }
                
                quality_score = tracker.score_deal_quality(deal_info)
                
                # Generate reply suggestion
                reply = classifier.generate_reply_suggestion(
                    message_text=inquiry.get("text", ""),
                    category=inquiry["category"],
                    sender_name=inquiry["sender"],
                )
                
                scored_deals.append({
                    "message_id": inquiry["message_id"],
                    "sender": inquiry["sender"],
                    "category": inquiry["category"],
                    "quality_score": quality_score,
                    "suggested_reply": reply,
                    "deal_info": deal_info,
                })
        
        # Mock deal pipeline data
        mock_deals = [
            {"status": "inquiry", "offered_amount": 5000},
            {"status": "negotiating", "offered_amount": 3000},
            {"status": "in_progress", "offered_amount": 4000},
            {"status": "completed", "offered_amount": 6000},
        ]
        
        pipeline_analysis = tracker.track_deal_pipeline(mock_deals)
        
        # Build result
        result = {
            "dms_analyzed": len(classified_dms),
            "business_inquiries": len(business_inquiries),
            "deals_scored": len(scored_deals),
            "classified_dms": classified_dms,
            "business_inquiries_detail": business_inquiries,
            "scored_deals": scored_deals,
            "pipeline_analysis": pipeline_analysis,
        }
        
        state["agent_results"]["collaboration_business"] = result
        state["active_agents"].append("collaboration_business")
        
        # Generate insights for high-quality deals
        for deal in scored_deals:
            quality = deal["quality_score"]
            if quality["overall_score"] >= 0.75:
                state["insights"].append({
                    "type": "business_opportunity",
                    "priority": 9,
                    "title": f"💼 {deal['sender']}: {quality['grade']} Grade Deal",
                    "body": f"{quality['recommendation']} Estimated value: ${deal['deal_info']['offered_amount']:,}",
                    "action": {"type": "view_deal", "deal_data": deal},
                })
            elif quality["red_flags"]:
                state["insights"].append({
                    "type": "deal_warning",
                    "priority": 8,
                    "title": f"⚠️ {deal['sender']}: Red Flags Detected",
                    "body": f"{len(quality['red_flags'])} red flag(s): {', '.join(quality['red_flags'][:2])}",
                    "action": {"type": "view_deal", "deal_data": deal},
                })
        
        # Generate insight for pipeline
        if pipeline_analysis["active_deals"] > 0:
            state["insights"].append({
                "type": "pipeline_update",
                "priority": 6,
                "title": f"📊 {pipeline_analysis['active_deals']} Active Deals",
                "body": f"Total value: ${pipeline_analysis['total_value']:,}. Conversion rate: {pipeline_analysis['conversion_rate']:.1%}",
                "action": {"type": "view_pipeline"},
            })
        
        log.info("agent.collaboration_business.completed",
                 workspace_id=state["workspace_id"],
                 business_inquiries=len(business_inquiries),
                 deals_scored=len(scored_deals))
    
    except Exception as e:
        log.error("agent.collaboration_business.failed",
                  workspace_id=state["workspace_id"],
                  error=str(e),
                  error_type=type(e).__name__)
        
        # Return error state
        state["agent_results"]["collaboration_business"] = {
            "dms_analyzed": 0,
            "error": str(e),
        }
        state["active_agents"].append("collaboration_business")
        state["errors"].append(f"collaboration_business: {str(e)}")
    
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT ALL AGENT NODES
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "niche_intelligence_agent",
    "trend_detection_agent",
    "analytics_intelligence_agent",
    "competitor_intelligence_agent",
    "content_ideation_agent",
    "goal_accountability_agent",
    "news_research_agent",
    "tips_tricks_agent",
    "smart_scheduling_agent",
    "growth_optimization_agent",
    "video_intelligence_agent",
    "predictive_virality_agent",
    "collaboration_business_agent",
    "approval_gate",
]
