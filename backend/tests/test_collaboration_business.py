"""Tests for Collaboration & Business Agent services."""
import pytest
from app.services.collaboration.dm_classifier import DMClassifier
from app.services.collaboration.deal_tracker import DealTracker


class TestDMClassifier:
    """Test the DMClassifier service."""
    
    def test_init(self):
        """Test classifier initialization."""
        classifier = DMClassifier()
        assert classifier is not None
        assert len(classifier.CATEGORY_KEYWORDS) > 0
    
    def test_classify_brand_deal(self):
        """Test classifying a brand deal message."""
        classifier = DMClassifier()
        
        result = classifier.classify_message(
            "Hi! We'd love to partner with you for a sponsored campaign. We have a budget for this promotion.",
            sender_followers=50000,
            sender_verified=True,
        )
        
        assert result["category"] == "brand_deal"
        assert result["is_business_inquiry"] is True
        assert result["priority"] == 10
        assert 0 <= result["confidence"] <= 1
    
    def test_classify_collab(self):
        """Test classifying a collaboration request."""
        classifier = DMClassifier()
        
        result = classifier.classify_message(
            "Hey! Want to collab on a video together? I think it would be great!",
        )
        
        assert result["category"] == "collab"
        assert result["is_business_inquiry"] is True
        assert result["priority"] == 8
    
    def test_classify_fan_message(self):
        """Test classifying a fan message."""
        classifier = DMClassifier()
        
        result = classifier.classify_message(
            "Love your content! You're amazing and inspire me every day!",
        )
        
        assert result["category"] == "fan"
        assert result["is_business_inquiry"] is False
        assert result["priority"] == 4
    
    def test_classify_spam(self):
        """Test classifying spam."""
        classifier = DMClassifier()
        
        result = classifier.classify_message(
            "Click here now! Make money fast! Limited time offer!",
        )
        
        assert result["category"] == "spam"
        assert result["priority"] == 1
    
    def test_sentiment_analysis(self):
        """Test sentiment analysis."""
        classifier = DMClassifier()
        
        # Positive sentiment
        positive = classifier.classify_message("I love your content! It's amazing!")
        assert positive["sentiment"]["label"] == "positive"
        
        # Negative sentiment
        negative = classifier.classify_message("This is terrible and disappointing.")
        assert negative["sentiment"]["label"] == "negative"
    
    def test_generate_reply_suggestion(self):
        """Test reply suggestion generation."""
        classifier = DMClassifier()
        
        # Brand deal reply
        brand_reply = classifier.generate_reply_suggestion(
            "Partnership opportunity",
            "brand_deal",
            "BrandName"
        )
        assert "BrandName" in brand_reply
        assert len(brand_reply) > 0
        
        # Fan reply
        fan_reply = classifier.generate_reply_suggestion(
            "Love your content",
            "fan",
            "Fan123"
        )
        assert "Fan123" in fan_reply
        
        # Spam (no reply)
        spam_reply = classifier.generate_reply_suggestion(
            "Spam message",
            "spam"
        )
        assert spam_reply is None
    
    def test_batch_classify(self):
        """Test batch classification."""
        classifier = DMClassifier()
        
        messages = [
            {"id": "1", "text": "Partnership opportunity", "sender": "Brand"},
            {"id": "2", "text": "Love your content!", "sender": "Fan"},
        ]
        
        results = classifier.batch_classify(messages)
        
        assert len(results) == 2
        assert all("category" in r for r in results)
        assert all("message_id" in r for r in results)
    
    def test_get_business_inquiries(self):
        """Test filtering business inquiries."""
        classifier = DMClassifier()
        
        classified = [
            {"is_business_inquiry": True, "priority": 10, "category": "brand_deal"},
            {"is_business_inquiry": False, "priority": 4, "category": "fan"},
            {"is_business_inquiry": True, "priority": 8, "category": "collab"},
        ]
        
        business = classifier.get_business_inquiries(classified)
        
        assert len(business) == 2
        assert business[0]["priority"] == 10  # Sorted by priority


class TestDealTracker:
    """Test the DealTracker service."""
    
    def test_init(self):
        """Test tracker initialization."""
        tracker = DealTracker()
        assert tracker is not None
        assert len(tracker.QUALITY_FACTORS) > 0
    
    def test_score_high_quality_deal(self):
        """Test scoring a high-quality deal."""
        tracker = DealTracker()
        
        deal = {
            "brand_followers": 150000,
            "brand_verified": True,
            "offered_amount": 5000,
            "creator_followers": 10000,
            "niche_match": 0.9,
            "deliverables": ["1 post", "1 story"],
            "deadline_days": 30,
            "description": "Great partnership opportunity",
            "terms": "Standard terms",
        }
        
        result = tracker.score_deal_quality(deal)
        
        assert result["overall_score"] > 0.7
        assert result["grade"] in ["A", "B", "C"]
        assert "score_breakdown" in result
        assert len(result["red_flags"]) == 0
    
    def test_score_low_quality_deal(self):
        """Test scoring a low-quality deal."""
        tracker = DealTracker()
        
        deal = {
            "brand_followers": 1000,
            "brand_verified": False,
            "offered_amount": 0,  # No compensation
            "creator_followers": 10000,
            "niche_match": 0.3,
            "deliverables": ["post1", "post2", "post3", "post4", "post5"],
            "deadline_days": 3,  # Too rushed
            "description": "Work for exposure only",
            "terms": "",
        }
        
        result = tracker.score_deal_quality(deal)
        
        assert result["overall_score"] < 0.6
        assert result["grade"] in ["D", "F"]
        assert len(result["red_flags"]) > 0
    
    def test_detect_red_flags(self):
        """Test red flag detection."""
        tracker = DealTracker()
        
        deal = {
            "description": "We need unlimited exclusivity and all rights to your content",
            "terms": "Work for free, exposure only",
            "offered_amount": 0,
        }
        
        result = tracker.score_deal_quality(deal)
        
        assert len(result["red_flags"]) > 0
        assert any("exclusivity" in flag or "free" in flag for flag in result["red_flags"])
    
    def test_track_deal_pipeline(self):
        """Test pipeline tracking."""
        tracker = DealTracker()
        
        deals = [
            {"status": "inquiry", "offered_amount": 1000},
            {"status": "negotiating", "offered_amount": 2000},
            {"status": "in_progress", "offered_amount": 3000},
            {"status": "completed", "offered_amount": 4000},
            {"status": "completed", "offered_amount": 5000},
        ]
        
        result = tracker.track_deal_pipeline(deals)
        
        assert result["total_deals"] == 5
        assert result["active_deals"] == 2  # negotiating + in_progress
        assert result["completed_deals"] == 2
        assert result["total_value"] == 12000  # contract_sent + in_progress + completed
        assert result["conversion_rate"] > 0
    
    def test_suggest_counter_offer(self):
        """Test counter-offer suggestions."""
        tracker = DealTracker()
        
        # Low compensation deal
        deal = {
            "offered_amount": 100,
            "creator_followers": 10000,
            "deadline_days": 5,
            "deliverables": ["post1", "post2", "post3", "post4"],
        }
        
        quality_score = tracker.score_deal_quality(deal)
        suggestions = tracker.suggest_counter_offer(deal, quality_score)
        
        assert suggestions is not None
        assert "compensation" in suggestions or "timeline" in suggestions or "deliverables" in suggestions
    
    def test_no_counter_offer_for_good_deal(self):
        """Test that good deals don't get counter-offers."""
        tracker = DealTracker()
        
        # Good deal
        deal = {
            "brand_followers": 100000,
            "brand_verified": True,
            "offered_amount": 5000,
            "creator_followers": 10000,
            "niche_match": 0.9,
            "deliverables": ["1 post"],
            "deadline_days": 30,
            "description": "Great opportunity",
            "terms": "Standard",
        }
        
        quality_score = tracker.score_deal_quality(deal)
        suggestions = tracker.suggest_counter_offer(deal, quality_score)
        
        assert suggestions is None  # No counter-offer needed


# Agent integration tests would go here
# These require database fixtures and are similar to other agent tests
