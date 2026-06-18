"""Agent orchestration service - coordinates all agents."""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import structlog

log = structlog.get_logger(__name__)


class AgentOrchestrator:
    """Coordinate agent execution based on triggers and priorities."""
    
    # Agent execution frequencies
    AGENT_SCHEDULES = {
        "niche_intelligence": {"frequency": "every_6h", "priority": 8},
        "trend_detection": {"frequency": "every_30m", "priority": 10},
        "analytics_intelligence": {"frequency": "daily", "priority": 7},
        "competitor_intelligence": {"frequency": "every_4h", "priority": 9},
        "content_ideation": {"frequency": "daily", "priority": 6},
        "goal_accountability": {"frequency": "daily", "priority": 8},
        "collaboration_business": {"frequency": "real_time", "priority": 10},
        "news_research": {"frequency": "hourly", "priority": 5},
        "tips_tricks": {"frequency": "weekly", "priority": 4},
        "smart_scheduling": {"frequency": "weekly", "priority": 6},
        "growth_optimization": {"frequency": "daily", "priority": 7},
        "video_intelligence": {"frequency": "on_demand", "priority": 8},
        "predictive_virality": {"frequency": "on_demand", "priority": 9},
    }
    
    # Cost budgets per agent (USD)
    AGENT_COST_BUDGETS = {
        "niche_intelligence": 0.005,
        "trend_detection": 0.015,
        "analytics_intelligence": 0.010,
        "competitor_intelligence": 0.010,
        "content_ideation": 0.008,
        "goal_accountability": 0.003,
        "collaboration_business": 0.000,  # No LLM
        "news_research": 0.005,
        "tips_tricks": 0.005,
        "smart_scheduling": 0.000,  # No LLM
        "growth_optimization": 0.000,  # No LLM
        "video_intelligence": 0.000,  # No LLM
        "predictive_virality": 0.000,  # No LLM
    }
    
    def __init__(self):
        """Initialize orchestrator."""
        self.total_budget = 0.10  # $0.10 per orchestration run
        self.agent_costs = {}
    
    def determine_agents_to_run(
        self,
        trigger: str,
        user_context: Dict,
        last_run_times: Optional[Dict[str, datetime]] = None,
    ) -> List[str]:
        """Determine which agents should run based on trigger and context.
        
        Args:
            trigger: What triggered this orchestration (scheduled, user_request, event, webhook)
            user_context: User's workspace context (niche, goals, accounts, etc.)
            last_run_times: When each agent last ran
            
        Returns:
            List of agent names to execute
        """
        agents_to_run = []
        now = datetime.utcnow()
        last_run_times = last_run_times or {}
        
        if trigger == "user_request":
            # User explicitly requested - run all relevant agents
            agents_to_run = list(self.AGENT_SCHEDULES.keys())
        
        elif trigger == "scheduled":
            # Check which agents are due based on their schedule
            for agent_name, config in self.AGENT_SCHEDULES.items():
                frequency = config["frequency"]
                last_run = last_run_times.get(agent_name)
                
                if self._should_run_agent(agent_name, frequency, last_run, now):
                    agents_to_run.append(agent_name)
        
        elif trigger == "webhook":
            # Webhook events trigger specific agents
            agents_to_run = ["collaboration_business", "analytics_intelligence"]
        
        elif trigger == "event":
            # Event-driven (e.g., new post published)
            event_type = user_context.get("event_type")
            
            if event_type == "post_published":
                agents_to_run = ["analytics_intelligence", "predictive_virality"]
            elif event_type == "video_uploaded":
                agents_to_run = ["video_intelligence"]
            elif event_type == "goal_deadline_approaching":
                agents_to_run = ["goal_accountability"]
        
        # Filter based on user subscription tier
        subscription_tier = user_context.get("subscription_tier", "free")
        agents_to_run = self._filter_by_subscription(agents_to_run, subscription_tier)
        
        # Sort by priority (highest first)
        agents_to_run.sort(
            key=lambda x: self.AGENT_SCHEDULES.get(x, {}).get("priority", 5),
            reverse=True
        )
        
        return agents_to_run
    
    def _should_run_agent(
        self,
        agent_name: str,
        frequency: str,
        last_run: Optional[datetime],
        now: datetime,
    ) -> bool:
        """Check if agent should run based on frequency."""
        if not last_run:
            return True  # Never run before
        
        time_since_last_run = now - last_run
        
        frequency_map = {
            "every_30m": timedelta(minutes=30),
            "hourly": timedelta(hours=1),
            "every_4h": timedelta(hours=4),
            "every_6h": timedelta(hours=6),
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
        }
        
        threshold = frequency_map.get(frequency)
        if not threshold:
            return False  # on_demand or real_time agents don't run on schedule
        
        return time_since_last_run >= threshold
    
    def _filter_by_subscription(
        self,
        agents: List[str],
        subscription_tier: str,
    ) -> List[str]:
        """Filter agents based on subscription tier."""
        if subscription_tier == "free":
            # Free tier: only basic agents
            allowed = [
                "niche_intelligence",
                "trend_detection",
                "analytics_intelligence",
            ]
            return [a for a in agents if a in allowed]
        
        elif subscription_tier == "pro":
            # Pro tier: all except custom agents
            return agents
        
        else:  # business, enterprise
            # Full access
            return agents
    
    def prioritize_agents(
        self,
        agents: List[str],
        available_budget: float,
    ) -> List[str]:
        """Prioritize agents to fit within budget.
        
        Args:
            agents: List of agents to run
            available_budget: Available budget in USD
            
        Returns:
            Prioritized list of agents that fit budget
        """
        # Calculate total cost
        total_cost = sum(self.AGENT_COST_BUDGETS.get(a, 0) for a in agents)
        
        if total_cost <= available_budget:
            return agents  # All agents fit
        
        # Need to prioritize - sort by priority and cost efficiency
        agents_with_scores = []
        for agent in agents:
            priority = self.AGENT_SCHEDULES.get(agent, {}).get("priority", 5)
            cost = self.AGENT_COST_BUDGETS.get(agent, 0)
            
            # Score = priority / cost (higher is better)
            # Free agents (cost=0) get max score
            score = priority / cost if cost > 0 else 999
            
            agents_with_scores.append((agent, score, cost))
        
        # Sort by score (highest first)
        agents_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select agents that fit budget
        selected = []
        current_cost = 0
        
        for agent, score, cost in agents_with_scores:
            if current_cost + cost <= available_budget:
                selected.append(agent)
                current_cost += cost
        
        return selected
    
    def track_agent_cost(self, agent_name: str, cost: float):
        """Track cost for an agent execution."""
        if agent_name not in self.agent_costs:
            self.agent_costs[agent_name] = []
        
        self.agent_costs[agent_name].append({
            "timestamp": datetime.utcnow(),
            "cost": cost,
        })
    
    def get_cost_summary(self) -> Dict:
        """Get cost summary across all agents."""
        total_cost = sum(
            sum(run["cost"] for run in runs)
            for runs in self.agent_costs.values()
        )
        
        agent_totals = {
            agent: sum(run["cost"] for run in runs)
            for agent, runs in self.agent_costs.items()
        }
        
        return {
            "total_cost": round(total_cost, 6),
            "budget_remaining": round(self.total_budget - total_cost, 6),
            "budget_used_pct": round((total_cost / self.total_budget) * 100, 2),
            "agent_costs": {k: round(v, 6) for k, v in agent_totals.items()},
        }
    
    def should_retry_agent(
        self,
        agent_name: str,
        error: Exception,
        retry_count: int,
    ) -> bool:
        """Determine if agent should be retried after failure.
        
        Args:
            agent_name: Name of failed agent
            error: The exception that occurred
            retry_count: Number of retries so far
            
        Returns:
            True if should retry
        """
        max_retries = 3
        
        if retry_count >= max_retries:
            return False
        
        # Don't retry on certain errors
        non_retryable_errors = [
            "AuthenticationError",
            "PermissionError",
            "ValidationError",
        ]
        
        error_type = type(error).__name__
        if error_type in non_retryable_errors:
            return False
        
        # Retry on transient errors
        retryable_errors = [
            "TimeoutError",
            "ConnectionError",
            "RateLimitError",
            "ServiceUnavailableError",
        ]
        
        return error_type in retryable_errors
    
    def get_agent_dependencies(self, agent_name: str) -> List[str]:
        """Get agents that should run before this agent.
        
        Args:
            agent_name: Agent to check dependencies for
            
        Returns:
            List of agent names that should run first
        """
        dependencies = {
            "content_ideation": ["trend_detection", "competitor_intelligence"],
            "predictive_virality": ["trend_detection", "analytics_intelligence"],
            "smart_scheduling": ["analytics_intelligence"],
            "growth_optimization": ["analytics_intelligence", "competitor_intelligence"],
        }
        
        return dependencies.get(agent_name, [])
    
    def create_execution_plan(
        self,
        agents: List[str],
    ) -> List[List[str]]:
        """Create execution plan respecting dependencies.
        
        Args:
            agents: List of agents to execute
            
        Returns:
            List of agent batches (each batch can run in parallel)
        """
        # Build dependency graph
        remaining = set(agents)
        executed = set()
        batches = []
        
        while remaining:
            # Find agents with no unmet dependencies
            batch = []
            for agent in remaining:
                deps = self.get_agent_dependencies(agent)
                unmet_deps = set(deps) - executed
                
                if not unmet_deps:
                    batch.append(agent)
            
            if not batch:
                # Circular dependency or missing dependency
                # Just run remaining agents
                batch = list(remaining)
            
            batches.append(batch)
            executed.update(batch)
            remaining -= set(batch)
        
        return batches
