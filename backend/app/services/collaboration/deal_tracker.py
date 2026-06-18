"""Deal tracking and quality scoring service."""
from typing import Dict, List, Optional
from datetime import datetime
import structlog

log = structlog.get_logger(__name__)


class DealTracker:
    """Track and score collaboration deals."""
    
    # Deal quality factors
    QUALITY_FACTORS = {
        "brand_reputation": 0.25,
        "compensation": 0.30,
        "audience_fit": 0.20,
        "creative_freedom": 0.15,
        "timeline": 0.10,
    }
    
    # Red flags in deals
    RED_FLAGS = [
        "unlimited exclusivity",
        "no compensation",
        "free work",
        "exposure only",
        "all rights",
        "perpetual license",
        "no payment terms",
        "work for free",
        "unpaid",
    ]
    
    def score_deal_quality(
        self,
        deal: Dict,
    ) -> Dict:
        """Score deal quality (0-1).
        
        Args:
            deal: Deal information dict
            
        Returns:
            Quality score and breakdown
        """
        scores = {}
        
        # Brand reputation (based on follower count, verified status)
        brand_followers = deal.get("brand_followers", 0)
        brand_verified = deal.get("brand_verified", False)
        
        if brand_verified:
            scores["brand_reputation"] = 0.9
        elif brand_followers > 100000:
            scores["brand_reputation"] = 0.8
        elif brand_followers > 10000:
            scores["brand_reputation"] = 0.6
        else:
            scores["brand_reputation"] = 0.4
        
        # Compensation
        offered_amount = deal.get("offered_amount", 0)
        creator_followers = deal.get("creator_followers", 1000)
        
        # Rough benchmark: $10-50 per 1000 followers
        expected_min = (creator_followers / 1000) * 10
        expected_max = (creator_followers / 1000) * 50
        
        if offered_amount >= expected_max:
            scores["compensation"] = 1.0
        elif offered_amount >= expected_min:
            scores["compensation"] = 0.7
        elif offered_amount > 0:
            scores["compensation"] = 0.4
        else:
            scores["compensation"] = 0.1  # No compensation
        
        # Audience fit (based on niche match)
        niche_match = deal.get("niche_match", 0.5)  # 0-1
        scores["audience_fit"] = niche_match
        
        # Creative freedom (based on deliverables flexibility)
        deliverables_count = len(deal.get("deliverables", []))
        if deliverables_count <= 2:
            scores["creative_freedom"] = 0.9
        elif deliverables_count <= 4:
            scores["creative_freedom"] = 0.7
        else:
            scores["creative_freedom"] = 0.5
        
        # Timeline (reasonable deadline)
        deadline_days = deal.get("deadline_days", 30)
        if deadline_days >= 30:
            scores["timeline"] = 0.9
        elif deadline_days >= 14:
            scores["timeline"] = 0.7
        elif deadline_days >= 7:
            scores["timeline"] = 0.5
        else:
            scores["timeline"] = 0.3  # Too rushed
        
        # Calculate weighted overall score
        overall_score = sum(
            scores[factor] * weight
            for factor, weight in self.QUALITY_FACTORS.items()
        )
        
        # Detect red flags
        red_flags = self._detect_red_flags(deal)
        
        # Penalize for red flags
        if red_flags:
            overall_score *= (1 - (len(red_flags) * 0.1))  # -10% per red flag
        
        return {
            "overall_score": round(max(overall_score, 0), 3),
            "grade": self._get_grade(overall_score),
            "score_breakdown": {k: round(v, 3) for k, v in scores.items()},
            "red_flags": red_flags,
            "recommendation": self._get_recommendation(overall_score, red_flags),
        }
    
    def _detect_red_flags(self, deal: Dict) -> List[str]:
        """Detect red flags in deal terms."""
        detected_flags = []
        
        # Check deal description for red flag keywords
        description = deal.get("description", "").lower()
        terms = deal.get("terms", "").lower()
        combined_text = description + " " + terms
        
        for flag in self.RED_FLAGS:
            if flag in combined_text:
                detected_flags.append(flag)
        
        # Check for missing payment terms
        if not deal.get("offered_amount") and not deal.get("payment_type"):
            detected_flags.append("no payment terms specified")
        
        # Check for unreasonable exclusivity
        if deal.get("exclusivity_months", 0) > 12:
            detected_flags.append("excessive exclusivity period")
        
        return detected_flags
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def _get_recommendation(self, score: float, red_flags: List[str]) -> str:
        """Get recommendation based on score and red flags."""
        if red_flags:
            return f"⚠️ Proceed with caution - {len(red_flags)} red flag(s) detected. Review terms carefully."
        
        if score >= 0.8:
            return "✅ Excellent opportunity! This deal looks great."
        elif score >= 0.7:
            return "👍 Good opportunity. Consider negotiating for better terms."
        elif score >= 0.6:
            return "⚠️ Moderate opportunity. Negotiate compensation and terms."
        else:
            return "❌ Poor opportunity. Consider declining or requesting major improvements."
    
    def track_deal_pipeline(
        self,
        deals: List[Dict],
    ) -> Dict:
        """Analyze deal pipeline.
        
        Args:
            deals: List of deals with status
            
        Returns:
            Pipeline analysis
        """
        pipeline = {
            "inquiry": [],
            "negotiating": [],
            "contract_sent": [],
            "in_progress": [],
            "completed": [],
            "rejected": [],
        }
        
        for deal in deals:
            status = deal.get("status", "inquiry")
            if status in pipeline:
                pipeline[status].append(deal)
        
        # Calculate metrics
        total_deals = len(deals)
        active_deals = len(pipeline["negotiating"]) + len(pipeline["contract_sent"]) + len(pipeline["in_progress"])
        
        # Calculate total value
        total_value = sum(
            deal.get("offered_amount", 0)
            for deal in deals
            if deal.get("status") in ["contract_sent", "in_progress", "completed"]
        )
        
        # Calculate conversion rate
        completed = len(pipeline["completed"])
        conversion_rate = completed / total_deals if total_deals > 0 else 0
        
        return {
            "pipeline": {k: len(v) for k, v in pipeline.items()},
            "total_deals": total_deals,
            "active_deals": active_deals,
            "completed_deals": completed,
            "total_value": total_value,
            "conversion_rate": round(conversion_rate, 3),
            "avg_deal_value": round(total_value / completed, 2) if completed > 0 else 0,
        }
    
    def suggest_counter_offer(
        self,
        deal: Dict,
        quality_score: Dict,
    ) -> Optional[Dict]:
        """Suggest counter-offer terms.
        
        Args:
            deal: Original deal
            quality_score: Deal quality score
            
        Returns:
            Counter-offer suggestion or None
        """
        if quality_score["overall_score"] >= 0.8:
            return None  # Deal is already good
        
        suggestions = {}
        
        # Suggest higher compensation if low
        if quality_score["score_breakdown"]["compensation"] < 0.7:
            current = deal.get("offered_amount", 0)
            creator_followers = deal.get("creator_followers", 1000)
            suggested = (creator_followers / 1000) * 30  # $30 per 1K followers
            
            suggestions["compensation"] = {
                "current": current,
                "suggested": round(suggested, 2),
                "reason": "Compensation below market rate for your audience size",
            }
        
        # Suggest timeline extension if rushed
        if quality_score["score_breakdown"]["timeline"] < 0.7:
            current_days = deal.get("deadline_days", 7)
            suggested_days = max(current_days * 2, 14)
            
            suggestions["timeline"] = {
                "current_days": current_days,
                "suggested_days": suggested_days,
                "reason": "Timeline is too tight for quality content creation",
            }
        
        # Suggest reducing deliverables if too many
        if quality_score["score_breakdown"]["creative_freedom"] < 0.7:
            current_count = len(deal.get("deliverables", []))
            suggested_count = min(current_count - 1, 3)
            
            suggestions["deliverables"] = {
                "current_count": current_count,
                "suggested_count": suggested_count,
                "reason": "Too many deliverables may compromise quality",
            }
        
        return suggestions if suggestions else None
