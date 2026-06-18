"""Niche seed data — Global + Indian market niches.

Run this after migration to populate the niches table.
Each niche includes:
  - Slug, name, description, icon, color
  - Keywords for content matching
  - Default hashtags per platform
  - Content types common in this niche
  - Primary platforms
  - Source configuration for the intelligence pipeline
"""
from __future__ import annotations

import uuid

# Pre-generated stable UUIDs for niches (so FKs are deterministic)
NICHE_SEEDS: list[dict] = [
    # ─── Global Niches ──────────────────────────────────────────────────────
    {
        "slug": "tech",
        "name": "Technology",
        "description": "Software, AI, hardware, startups, developer culture",
        "icon": "💻",
        "color": "#00D4FF",
        "keywords": ["tech", "AI", "software", "coding", "startup", "developer", "programming", "SaaS", "machine learning"],
        "hashtags": ["#Tech", "#AI", "#Coding", "#Developer", "#Software", "#Startup", "#MachineLearning"],
        "content_types": ["short_video", "thread", "blog", "tutorial", "reel"],
        "platforms": ["youtube", "twitter", "linkedin", "instagram", "tiktok"],
        "source_config": {
            "rss": [
                "https://hnrss.org/frontpage",
                "https://techcrunch.com/feed/",
                "https://www.theverge.com/rss/index.xml",
            ],
            "subreddits": ["programming", "technology", "MachineLearning", "artificial"],
            "github_trending": True,
            "product_hunt": True,
            "arxiv_categories": ["cs.AI", "cs.LG", "cs.SE"],
        },
        "sort_order": 1,
    },
    {
        "slug": "fitness",
        "name": "Fitness & Health",
        "description": "Workouts, nutrition, wellness, bodybuilding, yoga",
        "icon": "💪",
        "color": "#FF6B35",
        "keywords": ["fitness", "gym", "workout", "nutrition", "health", "bodybuilding", "yoga", "diet", "wellness"],
        "hashtags": ["#Fitness", "#Gym", "#Workout", "#Health", "#FitLife", "#Nutrition", "#Wellness"],
        "content_types": ["reel", "short_video", "carousel", "story", "long_video"],
        "platforms": ["instagram", "youtube", "tiktok"],
        "source_config": {
            "rss": [
                "https://examine.com/feed/",
            ],
            "subreddits": ["fitness", "bodybuilding", "naturalbodybuilding", "yoga"],
        },
        "sort_order": 2,
    },
    {
        "slug": "finance",
        "name": "Finance & Investing",
        "description": "Personal finance, investing, crypto, stocks, financial literacy",
        "icon": "💰",
        "color": "#00C853",
        "keywords": ["finance", "investing", "stocks", "crypto", "money", "trading", "financial literacy", "wealth"],
        "hashtags": ["#Finance", "#Investing", "#Stocks", "#Crypto", "#Money", "#FinancialFreedom"],
        "content_types": ["thread", "short_video", "reel", "blog", "carousel"],
        "platforms": ["youtube", "twitter", "instagram", "linkedin"],
        "source_config": {
            "rss": [
                "https://www.reuters.com/finance/rss",
            ],
            "subreddits": ["investing", "personalfinance", "CryptoCurrency", "stocks"],
        },
        "sort_order": 3,
    },
    {
        "slug": "gaming",
        "name": "Gaming",
        "description": "Video games, esports, game reviews, streaming, game development",
        "icon": "🎮",
        "color": "#7C4DFF",
        "keywords": ["gaming", "esports", "game review", "streaming", "gamer", "PlayStation", "Xbox", "PC gaming"],
        "hashtags": ["#Gaming", "#Gamer", "#Esports", "#GameReview", "#GamingCommunity"],
        "content_types": ["long_video", "short_video", "reel", "stream_highlight"],
        "platforms": ["youtube", "tiktok", "twitter", "instagram"],
        "source_config": {
            "subreddits": ["gaming", "Games", "pcgaming", "indiegames"],
        },
        "sort_order": 4,
    },
    {
        "slug": "beauty",
        "name": "Beauty & Skincare",
        "description": "Makeup, skincare routines, beauty products, tutorials",
        "icon": "💄",
        "color": "#FF4081",
        "keywords": ["beauty", "skincare", "makeup", "cosmetics", "beauty tips", "GRWM", "tutorial"],
        "hashtags": ["#Beauty", "#Skincare", "#Makeup", "#GRWM", "#BeautyTips", "#SkincareRoutine"],
        "content_types": ["reel", "short_video", "carousel", "tutorial", "story"],
        "platforms": ["instagram", "youtube", "tiktok", "pinterest"],
        "source_config": {
            "subreddits": ["SkincareAddiction", "MakeupAddiction", "beauty"],
        },
        "sort_order": 5,
    },
    {
        "slug": "food",
        "name": "Food & Cooking",
        "description": "Recipes, cooking tutorials, food reviews, restaurant culture",
        "icon": "🍳",
        "color": "#FF9800",
        "keywords": ["food", "cooking", "recipe", "chef", "baking", "foodie", "cuisine", "restaurant"],
        "hashtags": ["#Food", "#Cooking", "#Recipe", "#Foodie", "#HomeCooking", "#Chef"],
        "content_types": ["reel", "short_video", "carousel", "long_video", "blog"],
        "platforms": ["instagram", "youtube", "tiktok", "pinterest"],
        "source_config": {
            "subreddits": ["Cooking", "food", "recipes", "MealPrepSunday"],
        },
        "sort_order": 6,
    },
    {
        "slug": "education",
        "name": "Education & Learning",
        "description": "Online learning, teaching, study tips, academic content, edtech",
        "icon": "📚",
        "color": "#2196F3",
        "keywords": ["education", "learning", "study", "teaching", "school", "university", "edtech", "knowledge"],
        "hashtags": ["#Education", "#Learning", "#StudyTips", "#Teaching", "#Knowledge", "#EdTech"],
        "content_types": ["long_video", "short_video", "carousel", "thread", "blog"],
        "platforms": ["youtube", "instagram", "linkedin", "twitter"],
        "source_config": {
            "subreddits": ["learnprogramming", "education", "GetStudying"],
        },
        "sort_order": 7,
    },
    {
        "slug": "travel",
        "name": "Travel & Adventure",
        "description": "Travel vlogs, destination guides, adventure sports, backpacking",
        "icon": "✈️",
        "color": "#00BCD4",
        "keywords": ["travel", "adventure", "explore", "wanderlust", "backpacking", "vlog", "destination"],
        "hashtags": ["#Travel", "#Wanderlust", "#Adventure", "#TravelVlog", "#Explore"],
        "content_types": ["reel", "long_video", "short_video", "carousel", "story"],
        "platforms": ["instagram", "youtube", "tiktok", "pinterest"],
        "source_config": {
            "subreddits": ["travel", "backpacking", "solotravel"],
        },
        "sort_order": 8,
    },
    {
        "slug": "comedy",
        "name": "Comedy & Entertainment",
        "description": "Skits, memes, standup, roasts, funny content, parodies",
        "icon": "😂",
        "color": "#FFEB3B",
        "keywords": ["comedy", "funny", "memes", "skit", "standup", "humor", "parody", "roast"],
        "hashtags": ["#Comedy", "#Funny", "#Memes", "#Humor", "#LOL", "#Skit"],
        "content_types": ["reel", "short_video", "skit", "meme"],
        "platforms": ["instagram", "youtube", "tiktok", "twitter"],
        "source_config": {
            "subreddits": ["funny", "memes", "standupshots"],
        },
        "sort_order": 9,
    },
    {
        "slug": "lifestyle",
        "name": "Lifestyle & Productivity",
        "description": "Daily routines, productivity, minimalism, self-improvement, habits",
        "icon": "🌟",
        "color": "#9C27B0",
        "keywords": ["lifestyle", "productivity", "routine", "self-improvement", "minimalism", "habits", "motivation"],
        "hashtags": ["#Lifestyle", "#Productivity", "#Routine", "#SelfImprovement", "#Motivation"],
        "content_types": ["reel", "short_video", "carousel", "blog", "thread"],
        "platforms": ["instagram", "youtube", "tiktok", "linkedin", "pinterest"],
        "source_config": {
            "subreddits": ["productivity", "selfimprovement", "getdisciplined"],
        },
        "sort_order": 10,
    },
    {
        "slug": "fashion",
        "name": "Fashion & Style",
        "description": "Fashion trends, outfit ideas, styling tips, streetwear, luxury",
        "icon": "👗",
        "color": "#E91E63",
        "keywords": ["fashion", "style", "outfit", "streetwear", "luxury", "OOTD", "trends"],
        "hashtags": ["#Fashion", "#Style", "#OOTD", "#Streetwear", "#FashionTrends"],
        "content_types": ["reel", "carousel", "short_video", "story"],
        "platforms": ["instagram", "tiktok", "pinterest", "youtube"],
        "source_config": {
            "subreddits": ["fashion", "streetwear", "malefashionadvice"],
        },
        "sort_order": 11,
    },
    {
        "slug": "music",
        "name": "Music & Audio",
        "description": "Music production, covers, original songs, music reviews, DJ",
        "icon": "🎵",
        "color": "#1DB954",
        "keywords": ["music", "musician", "producer", "singer", "DJ", "cover", "original", "beats"],
        "hashtags": ["#Music", "#Musician", "#Producer", "#Cover", "#OriginalMusic"],
        "content_types": ["reel", "short_video", "long_video", "story"],
        "platforms": ["youtube", "instagram", "tiktok", "twitter"],
        "source_config": {
            "subreddits": ["music", "WeAreTheMusicMakers", "hiphopheads"],
        },
        "sort_order": 12,
    },
    {
        "slug": "business",
        "name": "Business & Entrepreneurship",
        "description": "Startups, entrepreneurship, marketing, business growth, leadership",
        "icon": "📈",
        "color": "#795548",
        "keywords": ["business", "entrepreneur", "startup", "marketing", "leadership", "growth", "CEO"],
        "hashtags": ["#Business", "#Entrepreneur", "#Startup", "#Marketing", "#Leadership"],
        "content_types": ["thread", "carousel", "short_video", "blog", "long_video"],
        "platforms": ["linkedin", "twitter", "youtube", "instagram"],
        "source_config": {
            "subreddits": ["Entrepreneur", "smallbusiness", "startups"],
        },
        "sort_order": 13,
    },
    {
        "slug": "photography",
        "name": "Photography & Videography",
        "description": "Photography tips, gear reviews, editing, cinematography",
        "icon": "📷",
        "color": "#607D8B",
        "keywords": ["photography", "camera", "editing", "cinematography", "lightroom", "gear", "photo"],
        "hashtags": ["#Photography", "#Camera", "#PhotoOfTheDay", "#Cinematography"],
        "content_types": ["reel", "carousel", "tutorial", "long_video"],
        "platforms": ["instagram", "youtube", "tiktok", "pinterest"],
        "source_config": {
            "subreddits": ["photography", "videography", "cinematography"],
        },
        "sort_order": 14,
    },
    {
        "slug": "science",
        "name": "Science & Research",
        "description": "Space, physics, biology, chemistry, research explanations",
        "icon": "🔬",
        "color": "#4CAF50",
        "keywords": ["science", "research", "space", "physics", "biology", "chemistry", "NASA"],
        "hashtags": ["#Science", "#Research", "#Space", "#Physics", "#Biology"],
        "content_types": ["long_video", "short_video", "thread", "carousel"],
        "platforms": ["youtube", "twitter", "instagram", "tiktok"],
        "source_config": {
            "rss": [
                "https://www.nature.com/nature.rss",
            ],
            "subreddits": ["science", "space", "Physics", "biology"],
            "arxiv_categories": ["physics", "astro-ph", "q-bio"],
        },
        "sort_order": 15,
    },

    # ─── Indian-Specific Niches ─────────────────────────────────────────────
    {
        "slug": "indian-finance",
        "name": "Indian Finance & Markets",
        "description": "Indian stock market, mutual funds, tax planning, UPI, digital payments",
        "icon": "🇮🇳💰",
        "color": "#FF9933",
        "keywords": ["NSE", "BSE", "mutual funds", "SIP", "tax saving", "SEBI", "Nifty", "Sensex", "UPI"],
        "hashtags": ["#IndianFinance", "#StockMarket", "#MutualFunds", "#SIP", "#Nifty50"],
        "content_types": ["short_video", "thread", "carousel", "reel"],
        "platforms": ["youtube", "twitter", "instagram"],
        "source_config": {
            "rss": [
                "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
            ],
            "subreddits": ["IndiaInvestments", "IndianStreetBets"],
        },
        "sort_order": 101,
        "parent_slug": "finance",
    },
    {
        "slug": "indian-tech",
        "name": "Indian Tech & Startups",
        "description": "Indian startup ecosystem, IT industry, tech jobs, coding in India",
        "icon": "🇮🇳💻",
        "color": "#138808",
        "keywords": ["Indian startup", "Bangalore", "IT jobs", "Indian tech", "FAANG India", "placement"],
        "hashtags": ["#IndianStartup", "#TechIndia", "#Bangalore", "#IndianIT"],
        "content_types": ["thread", "short_video", "reel", "blog"],
        "platforms": ["twitter", "linkedin", "youtube", "instagram"],
        "source_config": {
            "subreddits": ["developersIndia", "IndianTech", "Bangalore"],
        },
        "sort_order": 102,
        "parent_slug": "tech",
    },
    {
        "slug": "indian-food",
        "name": "Indian Cuisine",
        "description": "Indian recipes, regional cuisine, street food, traditional cooking",
        "icon": "🇮🇳🍛",
        "color": "#D84315",
        "keywords": ["Indian food", "biryani", "curry", "street food", "Indian recipe", "desi food"],
        "hashtags": ["#IndianFood", "#DesiFood", "#IndianRecipe", "#StreetFood", "#Biryani"],
        "content_types": ["reel", "short_video", "carousel"],
        "platforms": ["instagram", "youtube", "tiktok"],
        "source_config": {
            "subreddits": ["IndianFood", "IndianCooking"],
        },
        "sort_order": 103,
        "parent_slug": "food",
    },
    {
        "slug": "indian-comedy",
        "name": "Desi Comedy",
        "description": "Indian memes, desi humor, Bollywood parodies, regional comedy",
        "icon": "🇮🇳😂",
        "color": "#FFC107",
        "keywords": ["desi comedy", "Indian memes", "Bollywood", "desi humor", "Indian funny"],
        "hashtags": ["#DesiComedy", "#IndianMemes", "#Bollywood", "#DesiHumor"],
        "content_types": ["reel", "short_video", "skit", "meme"],
        "platforms": ["instagram", "youtube", "twitter"],
        "source_config": {
            "subreddits": ["indianmemes", "BollyBlindsNGossip"],
        },
        "sort_order": 104,
        "parent_slug": "comedy",
    },
    {
        "slug": "indian-education",
        "name": "Indian Education & Exams",
        "description": "UPSC, JEE, NEET, competitive exams, Indian schooling system",
        "icon": "🇮🇳📚",
        "color": "#1565C0",
        "keywords": ["UPSC", "JEE", "NEET", "competitive exams", "Indian education", "board exams"],
        "hashtags": ["#UPSC", "#JEE", "#NEET", "#IndianEducation", "#StudyMotivation"],
        "content_types": ["long_video", "short_video", "carousel", "thread"],
        "platforms": ["youtube", "instagram", "twitter"],
        "source_config": {
            "subreddits": ["UPSC", "JEENEETards", "Indian_Academia"],
        },
        "sort_order": 105,
        "parent_slug": "education",
    },
]


async def seed_niches(db) -> int:
    """Seed niche definitions into the database.

    Returns the count of niches inserted. Skips existing slugs.
    """
    from sqlalchemy import select
    from app.domains.control.models import Niche

    inserted = 0
    parent_map: dict[str, uuid.UUID] = {}

    # First pass: insert all niches without parent references
    for niche_data in NICHE_SEEDS:
        existing = await db.execute(
            select(Niche).where(Niche.slug == niche_data["slug"])
        )
        if existing.scalar_one_or_none():
            # Already exists — grab ID for parent mapping
            result = await db.execute(
                select(Niche.id).where(Niche.slug == niche_data["slug"])
            )
            parent_map[niche_data["slug"]] = result.scalar_one()
            continue

        niche = Niche(
            slug=niche_data["slug"],
            name=niche_data["name"],
            description=niche_data.get("description"),
            icon=niche_data.get("icon"),
            color=niche_data.get("color"),
            keywords=niche_data.get("keywords"),
            hashtags=niche_data.get("hashtags"),
            content_types=niche_data.get("content_types"),
            platforms=niche_data.get("platforms"),
            source_config=niche_data.get("source_config"),
            sort_order=niche_data.get("sort_order", 0),
            is_active=True,
        )
        db.add(niche)
        await db.flush()
        parent_map[niche_data["slug"]] = niche.id
        inserted += 1

    # Second pass: set parent references for sub-niches
    for niche_data in NICHE_SEEDS:
        parent_slug = niche_data.get("parent_slug")
        if parent_slug and parent_slug in parent_map:
            niche_id = parent_map.get(niche_data["slug"])
            if niche_id:
                from sqlalchemy import update
                await db.execute(
                    update(Niche)
                    .where(Niche.id == niche_id)
                    .values(parent_niche_id=parent_map[parent_slug])
                )

    await db.commit()
    return inserted
