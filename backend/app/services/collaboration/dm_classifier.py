"""DM classification service for categorizing incoming messages.

Classifies messages into:
- brand_deal: Brand partnership opportunities
- collab: Collaboration requests from other creators
- fan: Fan messages and engagement
- spam: Spam or irrelevant messages
- question: Questions about content
- complaint: Complaints or negative feedback
"""
from typing import Dict, List, Optional
import re
import structlog

log = structlog.get_logger(__name__)


class DMClassifier:
    """Classify and analyze incoming DMs."""
    
    # Keywords for each category
    CATEGORY_KEYWORDS = {
        "brand_deal": [
            "partnership", "sponsor", "collaborate", "promotion", "campaign",
            "brand", "product", "advertise", "marketing", "paid",
            "budget", "rate", "compensation", "contract", "deal",
        ],
        "collab": [
            "collab", "collaboration", "work together", "joint", "feature",
            "guest", "interview", "podcast", "video together", "duet",
        ],
        "fan": [
            "love", "fan", "inspired", "amazing", "great content", "awesome",
            "thank you", "appreciate", "follow", "support",
        ],
        "spam": [
            "click here", "buy now", "limited time", "act now", "free money",
            "get rich", "work from home", "make money fast", "guaranteed",
        ],
        "question": [
            "how", "what", "when", "where", "why", "can you", "could you",
            "would you", "?", "help", "advice", "tips",
        ],
        "complaint": [
            "disappointed", "terrible", "worst", "hate", "angry", "upset",
            "complaint", "refund", "scam", "fake", "misleading",
        ],
    }
    
    # Priority scores for each category
    CATEGORY_PRIORITY = {
        "brand_deal": 10,
        "collab": 8,
        "question": 6,
        "complaint": 7,
        "fan": 4,
        "spam": 1,
    }
    
    def classify_message(
        self,
        message_text: str,
        sender_followers: Optional[int] = None,
        sender_verified: bool = False,
    ) -> Dict:
        """Classify a DM message.
        
        Args:
            message_text: The message content
            sender_followers: Optional follower count of sender
            sender_verified: Whether sender is verified
            
        Returns:
            Classification results with category, confidence, and priority
        """
        if not message_text:
            return {
                "category": "unknown",
                "confidence": 0.0,
                "priority": 5,
                "is_business_inquiry": False,
            }
        
        message_lower = message_text.lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            category_scores[category] = score
        
        # Get top category
        if max(category_scores.values()) == 0:
            top_category = "fan"  # Default to fan message
            confidence = 0.5
        else:
            top_category = max(category_scores.items(), key=lambda x: x[1])[0]
            total_matches = sum(category_scores.values())
            confidence = category_scores[top_category] / total_matches if total_matches > 0 else 0.5
        
        # Adjust confidence based on sender info
        if sender_verified:
            confidence = min(confidence + 0.1, 1.0)
        
        if sender_followers and sender_followers > 10000:
            confidence = min(confidence + 0.1, 1.0)
        
        # Determine if business inquiry
        is_business = top_category in ["brand_deal", "collab"]
        
        # Get priority
        priority = self.CATEGORY_PRIORITY.get(top_category, 5)
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(message_lower)
        
        return {
            "category": top_category,
            "confidence": round(confidence, 3),
            "priority": priority,
            "is_business_inquiry": is_business,
            "sentiment": sentiment,
            "category_scores": category_scores,
        }
    
    def _analyze_sentiment(self, message: str) -> Dict:
        """Analyze message sentiment."""
        positive_words = [
            "love", "great", "amazing", "awesome", "excellent", "fantastic",
            "wonderful", "perfect", "best", "thank", "appreciate",
        ]
        
        negative_words = [
            "hate", "terrible", "awful", "worst", "bad", "disappointed",
            "angry", "upset", "horrible", "disgusting",
        ]
        
        positive_count = sum(1 for word in positive_words if word in message)
        negative_count = sum(1 for word in negative_words if word in message)
        
        if positive_count > negative_count:
            sentiment_label = "positive"
            score = min(0.5 + (positive_count * 0.1), 1.0)
        elif negative_count > positive_count:
            sentiment_label = "negative"
            score = max(0.5 - (negative_count * 0.1), 0.0)
        else:
            sentiment_label = "neutral"
            score = 0.5
        
        return {
            "label": sentiment_label,
            "score": round(score, 3),
        }
    
    def generate_reply_suggestion(
        self,
        message_text: str,
        category: str,
        sender_name: Optional[str] = None,
    ) -> str:
        """Generate a suggested reply based on message category.
        
        Args:
            message_text: The original message
            category: Message category
            sender_name: Optional sender name
            
        Returns:
            Suggested reply text
        """
        name = sender_name or "there"
        
        reply_templates = {
            "brand_deal": f"Hi {name}! Thank you for reaching out. I'd love to learn more about this opportunity. Could you share more details about the partnership, timeline, and compensation? Looking forward to hearing from you!",
            
            "collab": f"Hey {name}! Thanks for the collaboration idea! I'm always open to working with fellow creators. What did you have in mind? Let's discuss how we can create something awesome together!",
            
            "fan": f"Thank you so much {name}! Your support means the world to me. I really appreciate you taking the time to reach out. Stay tuned for more content! 🙏",
            
            "question": f"Hi {name}! Great question! [Answer their question here]. Let me know if you need any other help!",
            
            "complaint": f"Hi {name}, I'm sorry to hear about your experience. I take all feedback seriously. Could you share more details so I can address this properly? Thank you for bringing this to my attention.",
            
            "spam": None,  # Don't reply to spam
        }
        
        return reply_templates.get(category, f"Hi {name}! Thanks for your message. I'll get back to you soon!")
    
    def batch_classify(
        self,
        messages: List[Dict],
    ) -> List[Dict]:
        """Classify multiple messages at once.
        
        Args:
            messages: List of message dicts with 'text', 'sender_followers', etc.
            
        Returns:
            List of classification results
        """
        results = []
        
        for msg in messages:
            classification = self.classify_message(
                message_text=msg.get("text", ""),
                sender_followers=msg.get("sender_followers"),
                sender_verified=msg.get("sender_verified", False),
            )
            
            # Add message ID for tracking
            classification["message_id"] = msg.get("id")
            classification["sender"] = msg.get("sender")
            
            results.append(classification)
        
        return results
    
    def get_business_inquiries(
        self,
        classified_messages: List[Dict],
    ) -> List[Dict]:
        """Filter for business inquiries only.
        
        Args:
            classified_messages: List of classified messages
            
        Returns:
            List of business inquiries sorted by priority
        """
        business_msgs = [
            msg for msg in classified_messages
            if msg.get("is_business_inquiry", False)
        ]
        
        # Sort by priority (highest first)
        business_msgs.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        return business_msgs
