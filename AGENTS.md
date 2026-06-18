# ContentFlow AI — Next-Gen Creator Intelligence Platform
## Complete System Design, Architecture & Product Blueprint

> **Version**: 1.0 | **Status**: Blueprint | **Target**: Web + iOS + Android  
> **Tagline**: *"Your AI-Powered Creator Co-Pilot — From Idea to Viral"*

---

## TABLE OF CONTENTS

1. [Vision & Problem Statement](#1-vision--problem-statement)
2. [Market Research & Competitor Analysis](#2-market-research--competitor-analysis)
3. [Tech Stack Decision](#3-tech-stack-decision)
4. [System Architecture Overview](#4-system-architecture-overview)
5. [Database Design](#5-database-design)
6. [Agent Orchestration System](#6-agent-orchestration-system)
7. [Content Intelligence & Fetching](#7-content-intelligence--fetching)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Video Editor Integration](#9-video-editor-integration)
10. [Analytics System](#10-analytics-system)
11. [Security Architecture](#11-security-architecture)
12. [API Design](#12-api-design)
13. [Deployment & Infrastructure](#13-deployment--infrastructure)
14. [Mobile Strategy](#14-mobile-strategy)
15. [Development Roadmap](#15-development-roadmap)
16. [Revenue Model](#16-revenue-model)

---

## 1. VISION & PROBLEM STATEMENT

### The Real World Problem

A solo content creator in 2025 does the job of a **10-person media company**:
- Researches trends (2–3 hrs/day)
- Scripts content (1–2 hrs/day)
- Edits video (3–5 hrs/day)
- Analyzes analytics (1 hr/day)
- Responds to DMs/collabs (1–2 hrs/day)
- Posts at optimal times across 6+ platforms
- Tracks competitors manually
- Hunts for brand deals
- Manages contracts

**They burn out. They miss trends. They post inconsistently. They leave money on the table.**

### The Solution: ContentFlow AI

**ContentFlow AI is a niche-aware, agentic creator operating system** that replaces the mental overhead of being a creator — giving them an always-on AI team that researches, recommends, schedules, analyzes, and manages their creator business while they focus on what only they can do: **create**.

### Core Value Props
- 🎯 **Niche-first personalization** — the entire app adapts to your content category
- 🤖 **Autonomous AI agent team** — not chatbots, actual task-completing agents
- 📈 **Competitor intelligence** — know what's working before you post
- ⏰ **Goal accountability** — weekly/monthly creation goals with AI reminders
- 💼 **Business automation** — deal tracking, contract drafting, DM screening
- 🌐 **Cross-platform in one dashboard** — IG, YT, TikTok, X, LinkedIn, Pinterest

---

## 2. MARKET RESEARCH & COMPETITOR ANALYSIS

### Primary Competitors

| Platform | What They Do | What They Miss |
|----------|-------------|----------------|
| **Buffer** | Scheduling + basic analytics | No AI agents, no niche intelligence, no competitor tracking |
| **Hootsuite** | Multi-platform posting | Expensive, UI is outdated, no content research AI |
| **Later** | Visual content calendar | Instagram-focused, no research or agent system |
| **Metricool** | Analytics + scheduling | No content generation, no trend detection |
| **Beehiiv** | Newsletter focus | Not social-media first |
| **Opus Clip** | Auto video clipping | Single feature, no full ecosystem |
| **Notion AI** | Content organization | Not creator-specific, no automation |
| **Taplio** | LinkedIn only | Single platform |

### What NONE of them have:
- ✅ Autonomous niche-aware AI agents
- ✅ Real-time competitor move tracking
- ✅ Goal + accountability system
- ✅ Business collaboration pipeline (DMs → Deals → Contracts)
- ✅ Niche-personalized content research and news feed
- ✅ Built-in video editor
- ✅ Trend prediction (not just detection)

### Our Unfair Advantage
We are building the **operating system for creators**, not just another scheduling tool.

---

## 3. TECH STACK DECISION

### The Mobile + Web Question: Next.js vs React Native vs Expo

**DECISION: Expo (React Native) for Mobile + Next.js 15 for Web, sharing a monorepo**

Here's why NOT Next.js alone for mobile:
- Next.js cannot natively compile to iOS/Android binaries
- "React Native for Web" via Expo is the correct pattern for universal apps
- You get **60fps native mobile** vs a PWA wrapper which feels sluggish

**The right architecture is a Turborepo monorepo:**

```
contentflow/
├── apps/
│   ├── web/          ← Next.js 15 (App Router) — full web app
│   ├── mobile/       ← Expo SDK 52 (iOS + Android)
│   └── api/          ← FastAPI backend
├── packages/
│   ├── ui/           ← Shared component library (Tamagui or NativeWind)
│   ├── types/        ← Shared TypeScript types
│   ├── api-client/   ← Shared API hooks (React Query)
│   └── agents/       ← Agent type definitions
```

### Full Stack Decision

#### Backend
| Layer | Technology | Why |
|-------|-----------|-----|
| **API Framework** | FastAPI (Python 3.12) | You know it, async-first, fast |
| **Agent Orchestration** | LangGraph 0.2 | State-machine agents, production-grade |
| **LLM Provider** | OpenAI GPT-4o + Anthropic Claude 3.5 | Fallback chain, cost optimization |
| **Task Queue** | Celery + Redis | Background agent tasks |
| **Message Broker** | Redis Pub/Sub + Celery | Real-time agent events |
| **Search** | Meilisearch | Full-text search across creator content |
| **Vector DB** | Qdrant | Semantic search, trend clustering |
| **Cache** | Redis | Session, rate limiting, hot data |
| **File Storage** | Cloudflare R2 (S3-compat) | Free egress, cheap |
| **Web Scraping** | Playwright + Crawlee | Competitor tracking |
| **RSS/News** | Feedparser + custom scrapers | Niche news feeds |

#### Frontend Web
| Layer | Technology | Why |
|-------|-----------|-----|
| **Framework** | Next.js 15 (App Router) | RSC, streaming, edge-ready |
| **Language** | TypeScript 5.5 | Type safety |
| **Styling** | Tailwind CSS v4 | Utility-first, fast |
| **Components** | shadcn/ui | Accessible, customizable |
| **State** | Zustand + React Query v5 | Server/client state split |
| **Animations** | Framer Motion | Smooth, professional |
| **Charts** | Recharts + Tremor | Analytics dashboards |
| **Video Editor** | Remotion (browser) | React-based video creation |
| **Real-time** | Socket.io / Pusher Channels | Agent event streaming |
| **Auth** | NextAuth.js v5 | OAuth flows |
| **Forms** | React Hook Form + Zod | Validation |

#### Frontend Mobile
| Layer | Technology | Why |
|-------|-----------|-----|
| **Framework** | Expo SDK 52 + React Native | Universal iOS/Android |
| **Navigation** | Expo Router (file-based) | Matches Next.js mental model |
| **Styling** | NativeWind (Tailwind for RN) | Share class names with web |
| **State** | Same Zustand + React Query | Code reuse |
| **Notifications** | Expo Notifications | Push for reminders/goals |
| **Camera** | Expo Camera | In-app content capture |
| **Video** | Expo Video + FFmpeg.kit | Mobile video editing |
| **Biometrics** | Expo LocalAuthentication | Face ID / fingerprint |

#### Infrastructure
| Layer | Technology | Why |
|-------|-----------|-----|
| **Hosting (API)** | Railway or Fly.io | Easy Docker, autoscale |
| **Hosting (Web)** | Vercel | Next.js optimized |
| **Mobile CI/CD** | EAS Build (Expo) | OTA updates, no app store wait |
| **Database** | Supabase (managed PostgreSQL) | Realtime + Auth + Row Security |
| **Monitoring** | Sentry + Grafana + Prometheus | Error tracking + metrics |
| **Logging** | Loki + Grafana | Structured log aggregation |
| **CDN** | Cloudflare | DDoS protection + caching |
| **Email** | Resend | Transactional emails |
| **Analytics** | PostHog (self-hostable) | Product analytics |

---

## 4. SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│   ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐ │
│   │  Next.js Web  │   │  Expo iOS    │   │  Expo Android      │ │
│   │  (Vercel)    │   │  App Store   │   │  Play Store        │ │
│   └──────┬───────┘   └──────┬───────┘   └────────┬───────────┘ │
└──────────┼───────────────────┼────────────────────┼─────────────┘
           │                   │                    │
           └───────────────────▼────────────────────┘
                               │  HTTPS / WSS
┌──────────────────────────────▼──────────────────────────────────┐
│                       API GATEWAY (FastAPI)                       │
│   ┌────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│   │   Auth     │  │  Rate Limit  │  │  Request Validation    │  │
│   │  Middleware│  │  (Redis)     │  │  (Pydantic v2)         │  │
│   └────────────┘  └──────────────┘  └────────────────────────┘  │
│                                                                   │
│   ┌────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│   │  REST API  │  │  WebSocket   │  │  Webhook Receivers     │  │
│   │  /v1/*     │  │  /ws/agent   │  │  /webhooks/*           │  │
│   └─────┬──────┘  └──────┬───────┘  └──────────┬─────────────┘  │
└─────────┼────────────────┼──────────────────────┼────────────────┘
          │                │                      │
┌─────────▼────────────────▼──────────────────────▼────────────────┐
│                      SERVICE LAYER                                 │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                  AGENT ORCHESTRATOR (LangGraph)              │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │ │
│  │  │  Niche   │ │  Trend   │ │Analytics │ │  Competitor    │  │ │
│  │  │  Agent   │ │  Agent   │ │  Agent   │ │    Agent       │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │ │
│  │  │  Content │ │  Goal/   │ │  Collab  │ │  News/Research │  │ │
│  │  │  Agent   │ │Reminder  │ │  Agent   │ │    Agent       │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │ │
│  │  │  Tips &  │ │Scheduling│ │  Video   │ │  Manipulation/ │  │ │
│  │  │  Tricks  │ │  Agent   │ │  Agent   │ │  Growth Agent  │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────────────────────┐ │
│  │  Content   │ │   Social     │ │       Analytics              │ │
│  │  Service   │ │   Platform   │ │       Service                │ │
│  └────────────┘ │   Connectors │ └──────────────────────────────┘ │
│                 └──────────────┘                                   │
└────────────────────────────────────────────────────────────────────┘
          │                │                │              │
┌─────────▼────────────────▼────────────────▼──────────────▼────────┐
│                       DATA LAYER                                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐  │
│  │ PostgreSQL │ │   Redis    │ │   Qdrant   │ │ Cloudflare R2  │  │
│  │ (Supabase) │ │  Cache/MQ  │ │  Vector DB │ │ Media Storage  │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────┘  │
│  ┌────────────┐ ┌────────────┐                                     │
│  │Meilisearch │ │  Celery    │                                     │
│  │Full-text   │ │  Workers   │                                     │
│  └────────────┘ └────────────┘                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 5. DATABASE DESIGN

### Design Principles
- **UUID primary keys** everywhere (no sequential IDs exposed)
- **Row Level Security** on Supabase for multi-tenant isolation
- **Soft deletes** with `deleted_at` timestamps
- **Audit columns**: `created_at`, `updated_at`, `created_by`
- **JSONB for flexible agent configs** (schema-less parts)
- **Partitioning** on analytics tables by month

---

### Core Schema (PostgreSQL)

```sql
-- ============================================================
-- USERS & ONBOARDING
-- ============================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE,
    display_name VARCHAR(100),
    avatar_url TEXT,
    cover_url TEXT,
    bio TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en',
    subscription_tier VARCHAR(20) DEFAULT 'free', -- free|pro|business|enterprise
    subscription_expires_at TIMESTAMPTZ,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_step INTEGER DEFAULT 0,
    email_verified BOOLEAN DEFAULT FALSE,
    phone VARCHAR(20),
    phone_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(100),
    last_login_at TIMESTAMPTZ,
    last_active_at TIMESTAMPTZ,
    login_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================
-- NICHE SYSTEM (Core to personalization)
-- ============================================================

CREATE TABLE niches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL, -- 'fitness', 'tech', 'cooking', etc.
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50), -- emoji or icon name
    color VARCHAR(7), -- hex color
    parent_niche_id UUID REFERENCES niches(id),
    keywords TEXT[], -- for content matching
    hashtags TEXT[], -- top platform hashtags
    content_types TEXT[], -- 'short_video','long_video','reel','blog','podcast'
    platforms TEXT[], -- primary platforms for this niche
    avg_posting_frequency JSONB, -- {"weekly": 5, "daily": 0.7}
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User can have multiple niches with primary flag
CREATE TABLE user_niches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    niche_id UUID NOT NULL REFERENCES niches(id),
    is_primary BOOLEAN DEFAULT FALSE,
    content_pillars TEXT[], -- user's specific sub-topics within niche
    target_audience JSONB, -- {"age_range":"18-35","gender":"mixed","interests":[...]}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, niche_id)
);

-- ============================================================
-- SOCIAL PLATFORM CONNECTIONS
-- ============================================================

CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(30) NOT NULL, -- 'instagram','youtube','tiktok','twitter','linkedin','pinterest','facebook'
    platform_user_id VARCHAR(200) NOT NULL,
    platform_username VARCHAR(100),
    platform_display_name VARCHAR(200),
    platform_avatar_url TEXT,
    platform_url TEXT,
    access_token TEXT, -- encrypted
    refresh_token TEXT, -- encrypted
    token_expires_at TIMESTAMPTZ,
    token_scope TEXT,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,4) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_primary BOOLEAN DEFAULT FALSE,
    last_synced_at TIMESTAMPTZ,
    sync_status VARCHAR(20) DEFAULT 'pending', -- pending|syncing|success|error
    error_message TEXT,
    permissions JSONB DEFAULT '{}', -- what we can read/write
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, platform, platform_user_id)
);

-- ============================================================
-- CONTENT MANAGEMENT
-- ============================================================

CREATE TABLE content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    niche_id UUID REFERENCES niches(id),
    title VARCHAR(500),
    caption TEXT,
    script TEXT, -- full script for video content
    content_type VARCHAR(30), -- 'reel','short','post','carousel','story','thread','blog'
    status VARCHAR(20) DEFAULT 'draft', -- draft|review|scheduled|published|archived|failed
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_score DECIMAL(3,2), -- AI quality score 0-1
    platforms TEXT[], -- ['instagram','tiktok','youtube']
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    
    -- Media references
    media_urls TEXT[],
    thumbnail_url TEXT,
    video_url TEXT,
    video_duration INTEGER, -- seconds
    
    -- Platform-specific overrides
    platform_configs JSONB DEFAULT '{}',
    -- {"instagram": {"caption": "...", "hashtags": [...], "location": "..."}}
    
    -- Performance after publishing
    total_views BIGINT DEFAULT 0,
    total_likes BIGINT DEFAULT 0,
    total_comments BIGINT DEFAULT 0,
    total_shares BIGINT DEFAULT 0,
    total_saves BIGINT DEFAULT 0,
    engagement_rate DECIMAL(6,4) DEFAULT 0,
    reach BIGINT DEFAULT 0,
    impressions BIGINT DEFAULT 0,
    
    -- Content metadata
    hashtags TEXT[],
    mentions TEXT[],
    tags TEXT[],
    content_pillars TEXT[],
    mood VARCHAR(50), -- 'educational','entertaining','inspirational','promotional'
    hooks TEXT[], -- first 3 second hooks tried
    
    -- AI analysis
    sentiment_score DECIMAL(3,2),
    readability_score DECIMAL(3,2),
    virality_score DECIMAL(3,2), -- predicted before posting
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE content_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    title VARCHAR(500),
    caption TEXT,
    script TEXT,
    changed_by UUID REFERENCES users(id),
    change_summary TEXT,
    snapshot JSONB, -- full content snapshot
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ANALYTICS (Partitioned by month)
-- ============================================================

CREATE TABLE content_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    social_account_id UUID REFERENCES social_accounts(id),
    platform VARCHAR(30) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    
    -- Engagement metrics
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    shares BIGINT DEFAULT 0,
    saves BIGINT DEFAULT 0,
    reach BIGINT DEFAULT 0,
    impressions BIGINT DEFAULT 0,
    profile_visits INTEGER DEFAULT 0,
    link_clicks INTEGER DEFAULT 0,
    
    -- Audience metrics
    engagement_rate DECIMAL(6,4),
    completion_rate DECIMAL(5,4), -- for videos
    avg_watch_time INTEGER, -- seconds
    
    -- Revenue metrics (for monetized creators)
    estimated_revenue DECIMAL(10,4) DEFAULT 0,
    rpm DECIMAL(8,4), -- revenue per mille
    
    -- Comment intelligence
    top_comments JSONB DEFAULT '[]',
    -- [{"text": "...", "likes": 150, "is_question": true, "sentiment": 0.8}]
    sentiment_breakdown JSONB DEFAULT '{}',
    -- {"positive": 0.7, "neutral": 0.2, "negative": 0.1}
    
    raw_data JSONB DEFAULT '{}', -- platform raw response
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (recorded_at);

-- Create monthly partitions
CREATE TABLE content_analytics_2025_01 PARTITION OF content_analytics
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
-- ... (auto-created by partition manager)

CREATE TABLE account_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    social_account_id UUID NOT NULL REFERENCES social_accounts(id),
    recorded_at TIMESTAMPTZ NOT NULL,
    followers_count BIGINT DEFAULT 0,
    followers_gained INTEGER DEFAULT 0,
    followers_lost INTEGER DEFAULT 0,
    following_count BIGINT DEFAULT 0,
    avg_engagement_rate DECIMAL(6,4),
    total_posts INTEGER DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    estimated_revenue DECIMAL(10,4) DEFAULT 0,
    audience_demographics JSONB DEFAULT '{}',
    top_locations JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (recorded_at);

-- ============================================================
-- GOALS & ACCOUNTABILITY
-- ============================================================

CREATE TABLE creator_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    goal_type VARCHAR(50), -- 'content_count','followers','views','revenue','engagement'
    period VARCHAR(20), -- 'daily','weekly','monthly','quarterly','yearly'
    target_value DECIMAL(15,4) NOT NULL,
    current_value DECIMAL(15,4) DEFAULT 0,
    unit VARCHAR(30), -- 'posts','followers','views','dollars'
    platform VARCHAR(30), -- null = all platforms
    status VARCHAR(20) DEFAULT 'active', -- active|paused|completed|failed|archived
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    reminder_enabled BOOLEAN DEFAULT TRUE,
    reminder_schedule JSONB DEFAULT '{}',
    -- {"days": ["monday","thursday"], "time": "09:00", "timezone": "Asia/Kolkata"}
    completed_at TIMESTAMPTZ,
    celebration_shown BOOLEAN DEFAULT FALSE,
    streak_count INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE goal_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES creator_goals(id) ON DELETE CASCADE,
    milestone_pct INTEGER NOT NULL, -- 25, 50, 75, 100
    reached_at TIMESTAMPTZ,
    celebration_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE goal_check_ins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES creator_goals(id) ON DELETE CASCADE,
    value_at_checkin DECIMAL(15,4),
    progress_pct DECIMAL(5,2),
    note TEXT,
    agent_analysis TEXT, -- AI analysis of progress
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AI AGENT SYSTEM
-- ============================================================

CREATE TABLE agent_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    -- 'niche_intelligence','trend','analytics','competitor','content_research',
    -- 'goal_reminder','collaboration','news_fetcher','tips_tricks','scheduling',
    -- 'growth','video_editor','manipulation'
    agent_name VARCHAR(100),
    is_enabled BOOLEAN DEFAULT TRUE,
    run_frequency VARCHAR(20) DEFAULT 'hourly',
    -- hourly|every_6h|daily|weekly|on_demand|real_time
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}',
    -- Agent-specific config: {"niches": ["tech"], "keywords": [...], "depth": "deep"}
    llm_model VARCHAR(50) DEFAULT 'gpt-4o',
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, agent_type)
);

CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_config_id UUID NOT NULL REFERENCES agent_configs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'running', -- running|success|failed|cancelled
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    error_message TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    steps JSONB DEFAULT '[]', -- LangGraph step trace
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    agent_run_id UUID REFERENCES agent_runs(id),
    insight_type VARCHAR(50),
    -- 'trend_alert','competitor_move','content_idea','goal_warning',
    -- 'collaboration_opportunity','growth_hack','posting_reminder','contract_opportunity'
    title VARCHAR(300) NOT NULL,
    body TEXT NOT NULL,
    action_url TEXT, -- deep link in app
    action_label TEXT,
    priority INTEGER DEFAULT 5, -- 1-10, 10 = highest
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    is_actioned BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TREND TRACKING
-- ============================================================

CREATE TABLE trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_id UUID REFERENCES niches(id),
    platform VARCHAR(30),
    trend_type VARCHAR(30), -- 'hashtag','sound','format','topic','challenge'
    title VARCHAR(300) NOT NULL,
    description TEXT,
    hashtags TEXT[],
    example_urls TEXT[],
    trend_score DECIMAL(5,2), -- 0-100 heat score
    trend_velocity DECIMAL(8,4), -- rate of growth per hour
    peak_predicted_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    peaked_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'rising', -- rising|peak|declining|dead|evergreen
    region VARCHAR(10) DEFAULT 'global',
    source VARCHAR(50), -- where we found it
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_trend_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    trend_id UUID NOT NULL REFERENCES trends(id),
    action VARCHAR(20), -- 'viewed','saved','used','dismissed'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COMPETITOR TRACKING
-- ============================================================

CREATE TABLE competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(30) NOT NULL,
    platform_username VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    avatar_url TEXT,
    profile_url TEXT,
    niche_id UUID REFERENCES niches(id),
    followers_count BIGINT DEFAULT 0,
    avg_engagement_rate DECIMAL(6,4),
    posting_frequency DECIMAL(5,2), -- posts per week
    is_active BOOLEAN DEFAULT TRUE,
    tracking_since TIMESTAMPTZ DEFAULT NOW(),
    last_tracked_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, platform, platform_username)
);

CREATE TABLE competitor_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    platform_post_id VARCHAR(200) UNIQUE,
    platform VARCHAR(30),
    content_type VARCHAR(30),
    caption TEXT,
    hashtags TEXT[],
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    shares BIGINT DEFAULT 0,
    engagement_rate DECIMAL(6,4),
    thumbnail_url TEXT,
    posted_at TIMESTAMPTZ,
    topics TEXT[], -- AI-extracted topics
    viral_score DECIMAL(5,2),
    why_it_worked TEXT, -- AI analysis
    content_gaps TEXT[], -- what they missed, our opportunity
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COLLABORATION & BUSINESS
-- ============================================================

CREATE TABLE collaborations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(30), -- 'brand_deal','collab','sponsorship','affiliate','ugc','pr'
    brand_name VARCHAR(200),
    brand_email VARCHAR(255),
    brand_website TEXT,
    contact_name VARCHAR(200),
    contact_platform VARCHAR(30),
    contact_handle VARCHAR(100),
    
    -- Deal details
    title VARCHAR(300),
    description TEXT,
    deliverables JSONB DEFAULT '[]',
    -- [{"type": "reel", "count": 2, "platform": "instagram", "deadline": "..."}]
    
    -- Financials
    offered_amount DECIMAL(12,2),
    negotiated_amount DECIMAL(12,2),
    final_amount DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'USD',
    payment_type VARCHAR(20), -- 'flat_fee','cpm','revenue_share','barter','hybrid'
    payment_status VARCHAR(20) DEFAULT 'pending',
    
    -- Status tracking
    status VARCHAR(30) DEFAULT 'inquiry',
    -- inquiry|negotiating|contract_sent|contract_signed|in_progress|completed|cancelled|rejected
    
    ai_score DECIMAL(3,2), -- AI deal quality score
    ai_recommendation TEXT, -- AI advice on this deal
    
    source VARCHAR(30), -- 'inbound_dm','email','outbound','platform'
    source_platform VARCHAR(30),
    
    deal_starts_at TIMESTAMPTZ,
    deal_ends_at TIMESTAMPTZ,
    deadline_at TIMESTAMPTZ,
    
    notes TEXT,
    internal_tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collaboration_id UUID NOT NULL REFERENCES collaborations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    contract_type VARCHAR(30) DEFAULT 'ai_generated',
    title VARCHAR(300),
    content TEXT, -- full contract text
    pdf_url TEXT, -- signed PDF
    status VARCHAR(20) DEFAULT 'draft', -- draft|sent|viewed|signed|countersigned|expired|voided
    signed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    signature_provider VARCHAR(30), -- 'docusign','hellosign','manual'
    external_contract_id VARCHAR(200),
    ai_review_summary TEXT, -- AI flags in contract
    ai_red_flags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE dm_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    social_account_id UUID REFERENCES social_accounts(id),
    platform VARCHAR(30),
    sender_platform_id VARCHAR(200),
    sender_username VARCHAR(100),
    sender_display_name VARCHAR(200),
    sender_avatar_url TEXT,
    sender_followers_count BIGINT,
    message_text TEXT,
    is_business_inquiry BOOLEAN DEFAULT FALSE,
    ai_category VARCHAR(30),
    -- 'brand_deal','collab','fan','spam','question','complaint','pr'
    ai_summary TEXT,
    ai_sentiment DECIMAL(3,2),
    ai_priority INTEGER DEFAULT 5, -- 1-10
    ai_suggested_reply TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    is_replied BOOLEAN DEFAULT FALSE,
    collaboration_id UUID REFERENCES collaborations(id),
    received_at TIMESTAMPTZ,
    platform_message_id VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CONTENT IDEAS & RESEARCH
-- ============================================================

CREATE TABLE content_ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    niche_id UUID REFERENCES niches(id),
    source VARCHAR(30), -- 'ai_generated','trend_derived','competitor_inspired','user_saved','news'
    title VARCHAR(500) NOT NULL,
    description TEXT,
    hook TEXT, -- suggested opening hook
    content_type VARCHAR(30),
    platforms TEXT[],
    hashtags TEXT[],
    estimated_virality DECIMAL(5,2),
    ai_rationale TEXT, -- why this will work
    related_trend_id UUID REFERENCES trends(id),
    source_url TEXT,
    status VARCHAR(20) DEFAULT 'new', -- new|saved|in_progress|used|dismissed
    priority INTEGER DEFAULT 5,
    expires_at TIMESTAMPTZ, -- trend-based ideas expire
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE saved_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    resource_type VARCHAR(30), -- 'article','video','tweet','post','research','tool'
    title VARCHAR(500),
    description TEXT,
    url TEXT,
    thumbnail_url TEXT,
    platform VARCHAR(30),
    author VARCHAR(200),
    niche_ids UUID[],
    ai_summary TEXT,
    ai_tags TEXT[],
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- POSTING SCHEDULE
-- ============================================================

CREATE TABLE posting_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    social_account_id UUID REFERENCES social_accounts(id),
    platform VARCHAR(30),
    day_of_week INTEGER[], -- 0=Sunday ... 6=Saturday
    time_slots TIME[], -- optimal times
    timezone VARCHAR(50),
    is_ai_optimized BOOLEAN DEFAULT TRUE,
    last_optimized_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- NEWS & CONTENT RESEARCH FEEDS
-- ============================================================

CREATE TABLE news_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_id UUID REFERENCES niches(id),
    source_type VARCHAR(20), -- 'rss','youtube_channel','twitter_account','subreddit','api'
    source_name VARCHAR(200),
    source_url TEXT,
    feed_url TEXT,
    platform VARCHAR(30),
    reliability_score DECIMAL(3,2) DEFAULT 0.8,
    is_active BOOLEAN DEFAULT TRUE,
    last_fetched_at TIMESTAMPTZ,
    articles_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES news_sources(id),
    niche_ids UUID[],
    title TEXT NOT NULL,
    description TEXT,
    content TEXT,
    author VARCHAR(200),
    url TEXT UNIQUE,
    thumbnail_url TEXT,
    published_at TIMESTAMPTZ,
    ai_summary TEXT,
    ai_tags TEXT[],
    ai_content_angle TEXT, -- how creator can use this
    relevance_score DECIMAL(5,4),
    engagement_score DECIMAL(5,4), -- how viral it went
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50),
    -- 'goal_reminder','trend_alert','competitor_move','new_insight',
    -- 'post_published','collab_update','contract_signed','milestone_reached'
    title VARCHAR(300),
    body TEXT,
    data JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT FALSE,
    is_push_sent BOOLEAN DEFAULT FALSE,
    is_email_sent BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 5,
    scheduled_for TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_social_accounts_user ON social_accounts(user_id) WHERE is_active = TRUE;
CREATE INDEX idx_content_items_user_status ON content_items(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_content_items_scheduled ON content_items(scheduled_at) WHERE status = 'scheduled';
CREATE INDEX idx_analytics_content_recorded ON content_analytics(content_id, recorded_at DESC);
CREATE INDEX idx_trends_niche_score ON trends(niche_id, trend_score DESC) WHERE status IN ('rising','peak');
CREATE INDEX idx_competitors_user ON competitors(user_id) WHERE is_active = TRUE;
CREATE INDEX idx_agent_insights_user_unread ON agent_insights(user_id, priority DESC) WHERE is_read = FALSE;
CREATE INDEX idx_dm_inbox_user_unread ON dm_inbox(user_id, ai_priority DESC) WHERE is_read = FALSE;
CREATE INDEX idx_content_ideas_user_status ON content_ideas(user_id, status, estimated_virality DESC);
CREATE INDEX idx_collaborations_user_status ON collaborations(user_id, status);
CREATE INDEX idx_news_articles_niche_relevance ON news_articles USING GIN(niche_ids);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, scheduled_for) WHERE is_read = FALSE;

-- Full-text search
CREATE INDEX idx_content_items_fts ON content_items USING GIN(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(caption,'')));
CREATE INDEX idx_news_articles_fts ON news_articles USING GIN(to_tsvector('english', title || ' ' || coalesce(description,'')));
```

---

## 6. AGENT ORCHESTRATION SYSTEM

### Architecture: LangGraph State Machine

Each agent is a **LangGraph StateGraph** with defined nodes, edges, and state schema. The **Master Orchestrator** decides which agents to invoke based on user context, time, and events.

```python
# agents/orchestrator.py

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator

class OrchestratorState(TypedDict):
    user_id: str
    user_context: dict  # niche, goals, accounts, preferences
    trigger: str        # 'scheduled'|'user_request'|'event'|'webhook'
    active_agents: List[str]
    agent_results: Annotated[dict, operator.or_]
    insights_generated: List[dict]
    actions_taken: List[str]
    errors: List[str]
    
# The orchestrator runs multiple agents in parallel using LangGraph's
# parallel node execution
```

### The 14 Agents

---

#### 1. 🧠 Niche Intelligence Agent
**Purpose**: Continuously learns and adapts to the creator's specific content niche  
**Runs**: Every 6 hours  
**Does**:
- Analyzes creator's past content performance by topic
- Identifies which content pillars perform best
- Suggests niche expansion or refinement
- Builds creator's unique audience interest graph
- Updates semantic embeddings in Qdrant for personalized recommendations

**Tech**: GPT-4o + Qdrant vector search + creator's historical data

---

#### 2. 📈 Trend Detection Agent
**Purpose**: Catch trends before they peak so creator can ride the wave  
**Runs**: Every 30 minutes  
**Sources scraped**:
- TikTok Discover page (Playwright)
- Twitter/X Trending (API + scraping)
- YouTube Trending
- Google Trends API
- Reddit rising posts (niche subreddits)
- Instagram Explore (Playwright)
- Pinterest Trends API

**Does**:
- Scores each trend 0-100 (heat score)
- Predicts when trend will peak
- Matches trends to user's niche and content style
- Generates a "how to make this content" brief
- Alerts user if trend velocity is exceptional

---

#### 3. 📊 Analytics Intelligence Agent
**Purpose**: Turn raw numbers into actionable creator intelligence  
**Runs**: Daily (deep), Real-time (on post publish)  
**Does**:
- Computes engagement rate benchmarks vs niche average
- Identifies best performing content types, hooks, lengths
- Analyzes **comment intelligence**: extracts questions, complaints, love, suggestions
- Detects optimal posting time based on your specific audience
- Generates weekly performance report with insights
- Flags underperforming content and diagnoses why
- Revenue attribution across content pieces

**Special Feature — Comment Intelligence**:
```
Top Questions to Answer in Next Video: [...]
Most Requested Topics: [...]
Negative Sentiment Clusters: [...]
Viral Comments You Should Reply To: [...]
```

---

#### 4. 🔍 Competitor Intelligence Agent
**Purpose**: Know exactly what competitors post, when, what works, what doesn't  
**Runs**: Every 4 hours  
**Does**:
- Scrapes competitor profiles (Playwright + rotating proxies)
- Tracks every new post within 30 mins of publishing
- Scores competitor content virality
- Extracts topics, hashtags, formats they're using
- Identifies content gaps (what they miss = your opportunity)
- Generates "steal the idea, do it better" briefs
- Tracks competitor follower growth trajectory
- Alerts if competitor does something unusually successful

**Output Example**:
> "MrBeast just posted a video using the 'impossible challenge' format. He got 2M views in 4 hours. His format: setup (30s) → attempts (8 mins) → climax (2 mins). Suggested angle for you: [tech niche equivalent]. Best posting window: within 18 hours before this trend saturates."

---

#### 5. 💡 Content Research & Ideation Agent
**Purpose**: Never run out of content ideas, always relevant, always timely  
**Runs**: Daily (batch), On-demand  
**Sources**:
- Niche news feeds (RSS, scraping)
- Trending YouTube videos in niche
- Reddit top posts (niche subreddits)
- Twitter viral posts in niche
- Google's "People Also Ask" mining
- Answer The Public API
- Product Hunt for tech creators
- Arxiv papers for science creators
- Patent filings for tech/business

**Does**:
- Generates 5-10 content ideas per day
- Each idea includes: title, hook, structure, hashtags, best platform, estimated virality
- Repurposing suggestions (turn blog into reel, reel into carousel)
- Seasonal content calendar suggestions
- Collaboration idea pairing with other creators

---

#### 6. 🎯 Goal & Accountability Agent
**Purpose**: Be the creator's digital coach that doesn't let them slack  
**Runs**: Daily check-in + event-triggered  
**Does**:
- Monitors goal progress in real-time
- Sends smart reminders (not annoying, contextual)
- If behind: calculates catch-up plan ("post 2 more reels this week")
- If ahead: celebrates and suggests stretch goals
- Weekly goal review with AI commentary
- Streak tracking and gamification
- Sends push notifications via Expo

**Reminder Logic**:
```
If user hasn't posted in 3 days AND goal is weekly_posts >= 5:
  → Send: "Hey [name]! You've posted 1/5 this week. 
           Here are 3 ideas you can shoot in 20 mins: [ideas]"
```

---

#### 7. 🤝 Collaboration & Business Agent
**Purpose**: Automate the entire business side of being a creator  
**Runs**: Continuously (webhook-driven for DMs) + Daily  
**Does**:
- Monitors DM inboxes across all connected platforms
- AI classifies incoming DMs (brand deal / collab / fan / spam)
- Scores deal quality (brand size, deal value, relevance to niche)
- Drafts personalized reply suggestions
- Tracks deal pipeline through stages
- Generates contract drafts using templates + GPT-4o
- Flags suspicious or bad-deal red flags
- Sends invoice reminders
- Tracks payment status
- Suggests outreach targets (brands in niche who are spending on creators)

**AI Red Flag Detection in Contracts**:
- Unlimited exclusivity clauses
- IP ownership grabs
- Missing payment terms
- Unusual liability clauses
- Unilateral termination without cause

---

#### 8. 📰 News & Research Agent
**Purpose**: Give creator a personalized intelligence briefing every morning  
**Runs**: Every hour  
**Sources** (niche-specific):
- **Tech**: TechCrunch, Hacker News, Product Hunt, ArXiv, GitHub Trending
- **Fitness**: PubMed, Men's Health, Examine.com, NSCA journals
- **Finance**: Bloomberg, Reuters, CNBC, SEC filings
- **Gaming**: IGN, Kotaku, Steam charts, Twitch trending
- **Food/Cooking**: Bon Appétit, NYT Cooking, Serious Eats
- **Beauty**: WWD, Allure, emerging brand launches
- **General**: Google News RSS, Twitter/X curated lists

**Does**:
- Fetches and summarizes articles
- Explains "why this matters for your content"
- Generates content angle from each news item
- Curated daily briefing in the app (your personalized TechCrunch/Morning Brew)

---

#### 9. 💡 Tips, Tricks & Platform Algorithm Agent
**Purpose**: Keep creator ahead of algorithm changes and growth hacks  
**Runs**: Weekly (deep dive), Real-time for algorithm changes  
**Sources**:
- Platform official creator blogs
- Creator economy newsletters (Dan Runcie, Jack Appleby)
- YouTube Creator Academy
- Social Media Examiner
- Scraping top creator Discord servers

**Does**:
- Tracks algorithm change announcements
- Tests posting strategies across creator's content
- Suggests format changes (carousel vs reel, long vs short)
- A/B test framework for thumbnails, captions, hooks
- Platform-specific growth hacks (e.g., "Use this TikTok hook pattern")
- Watch time optimization suggestions

---

#### 10. ⏰ Smart Scheduling Agent
**Purpose**: Post at exactly the right time to maximize reach  
**Runs**: Weekly recalculation + before each scheduled post  
**Does**:
- Analyzes creator's audience activity patterns
- Cross-references platform's peak traffic times
- Considers competitor posting schedule (avoid clashing)
- Timezone-aware for global audiences
- Adjusts for content type (reels peak at different times than carousels)
- Handles queue management and gap filling
- Suggests frequency per platform

---

#### 11. 📱 Growth & Engagement Optimization Agent (aka "Manipulation Agent")
**Purpose**: Ethically maximize reach, engagement, and follower growth  
**Runs**: Daily analysis + post-publish  
**Does**:
- Hashtag strategy optimization (not just popular, but reachable)
- Comment engagement timing (first 30 mins after posting is critical)
- Suggests which comments to reply to for algorithmic boost
- Caption optimization for SEO
- Cross-platform promotion strategy
- Thumbnail/cover image A/B testing recommendations
- CTA optimization (which CTAs drive most follows vs saves)
- Collab/duet strategy for follower growth
- Viral loop detection and replication

---

#### 12. 🎬 Video Intelligence Agent
**Purpose**: Make every video better before it's published  
**Runs**: On-demand (when video is uploaded)  
**Does**:
- Auto-generates captions (Whisper API)
- Suggests best clips for short-form (hook finder)
- Thumbnail generation (DALL-E 3 + best frame extraction)
- Hook effectiveness scoring
- Pacing analysis (detect slow spots)
- Sound/music suggestions (royalty-free)
- B-roll gap detection
- Chapter markers for YouTube
- Description SEO optimization

---

#### 13. 🧪 Predictive Virality Agent
**Purpose**: Predict how a piece of content will perform BEFORE posting  
**Runs**: On-demand pre-publish  
**Does**:
- Scores content on 12 virality signals:
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
- Explains what to improve
- Simulates likely outcome range (views, engagement)

---

#### 14. 🌐 Agent Orchestrator (Master)
**Purpose**: Coordinate all agents, prioritize tasks, manage costs  
**Runs**: Always  
**Does**:
- Determines which agents need to run based on triggers
- Manages agent execution queue (Celery)
- Handles agent failures with retry logic
- Enforces per-user API cost limits
- Streams agent progress to frontend via WebSocket
- Aggregates insights from all agents into unified feed
- Learns which agent outputs the user engages with most

### Agent Communication Protocol

```python
# All agents publish insights to Redis pub/sub
# Frontend subscribes via WebSocket

class AgentInsight(BaseModel):
    agent_type: str
    insight_type: str
    priority: int  # 1-10
    title: str
    body: str
    action: Optional[dict]
    expires_at: Optional[datetime]
    metadata: dict

# WebSocket message structure
{
  "type": "agent_insight",
  "agent": "trend_detection",
  "data": {
    "insight_type": "trend_alert",
    "priority": 9,
    "title": "🔥 Trending NOW: 'AI agents' content exploding on TikTok",
    "body": "This trend has 840% growth in the last 2 hours...",
    "action": {"type": "create_content", "idea_id": "uuid"}
  }
}
```

---

## 7. CONTENT INTELLIGENCE & FETCHING

### Niche-Specific Data Pipeline

```
User Niche(s) → Niche Config → Source Registry → Scrapers/APIs → 
Normalizer → AI Enrichment → Vector Embedding → Qdrant → 
Personalization Layer → User Feed
```

### How Niche Personalization Works

1. **Onboarding**: User picks niche(s) + content pillars + target audience
2. **Keyword Graph**: System builds keyword expansion graph (niche → topics → subtopics → keywords)
3. **Source Assignment**: Relevant RSS feeds, YouTube channels, subreddits, Twitter lists auto-assigned
4. **Semantic Filter**: All fetched content passes through niche semantic similarity filter (Qdrant)
5. **Relevance Scoring**: Content scored for this specific user based on their content history
6. **Continuous Learning**: User interactions (save/dismiss) retrain personalization weights

### Scraping Architecture

```python
# Playwright cluster with anti-detection
SCRAPER_CONFIG = {
    "proxy_rotation": True,
    "fingerprint_randomization": True,
    "human_behavior_simulation": True,  # random delays, mouse movement
    "session_rotation_after_n_requests": 50,
    "rate_limiting": "adaptive",  # backs off if getting 429s
}
```

### Content Sources by Niche

```yaml
fitness:
  rss:
    - https://www.menshealth.com/rss/all.xml
    - https://examine.com/feed/
    - https://pubmed.ncbi.nlm.nih.gov/rss/  
  youtube_channels:
    - "@AthleanX"
    - "@JeffNippard"
    - "@RenaissancePeriodization"
  subreddits:
    - r/fitness
    - r/bodybuilding
    - r/naturalbodybuilding
  twitter_lists: ["fitness_researchers", "sports_scientists"]

tech:
  rss:
    - https://hnrss.org/frontpage
    - https://techcrunch.com/feed/
    - https://www.theverge.com/rss/index.xml
  youtube_channels:
    - "@Fireship"
    - "@TheVerge"
    - "@TechLinked"
  github_trending: true
  product_hunt: true
  arxiv_categories: ["cs.AI", "cs.LG", "cs.SE"]
  subreddits:
    - r/programming
    - r/technology
    - r/MachineLearning
```

---

## 8. FRONTEND ARCHITECTURE

### App Structure (Next.js 15 Web)

```
app/
├── (auth)/
│   ├── login/page.tsx
│   ├── register/page.tsx
│   └── onboarding/
│       ├── step-1-niche/page.tsx
│       ├── step-2-platforms/page.tsx
│       ├── step-3-goals/page.tsx
│       └── step-4-competitors/page.tsx
├── (dashboard)/
│   ├── layout.tsx              ← Main app shell
│   ├── page.tsx                ← Home / Command Center
│   ├── insights/page.tsx       ← All agent insights feed
│   ├── content/
│   │   ├── page.tsx            ← Content calendar
│   │   ├── create/page.tsx     ← Content creator
│   │   ├── [id]/page.tsx       ← Content detail
│   │   └── ideas/page.tsx      ← AI generated ideas
│   ├── analytics/
│   │   ├── page.tsx            ← Analytics dashboard
│   │   └── [platform]/page.tsx ← Per-platform analytics
│   ├── trends/page.tsx         ← Trend radar
│   ├── competitors/
│   │   ├── page.tsx            ← Competitor overview
│   │   └── [id]/page.tsx       ← Single competitor deep dive
│   ├── goals/page.tsx          ← Goals & accountability
│   ├── inbox/
│   │   ├── page.tsx            ← DM inbox (all platforms)
│   │   └── collaborations/
│   │       ├── page.tsx        ← Collab pipeline
│   │       └── [id]/page.tsx   ← Single collaboration
│   ├── schedule/page.tsx       ← Posting calendar
│   ├── studio/
│   │   ├── page.tsx            ← Video editor
│   │   └── assets/page.tsx     ← Media library
│   ├── news/page.tsx           ← Niche news briefing
│   └── settings/
│       ├── page.tsx
│       ├── accounts/page.tsx   ← Connected socials
│       ├── agents/page.tsx     ← Agent configuration
│       ├── billing/page.tsx
│       └── security/page.tsx
├── api/
│   ├── auth/[...nextauth]/route.ts
│   └── webhooks/[platform]/route.ts
```

### Design System & UX Philosophy

**Visual Direction**: "Control room meets creative studio"
- Dark mode primary (deep slate, not pure black)
- Neon accent colors per niche (fitness = orange, tech = cyan, etc.)
- Card-based layout with glassmorphism accents
- Real-time data always visible (live follower count, today's stats)
- Agent activity shown as a live ticker/feed

**Key UI Patterns**:
- **Command Bar** (Cmd+K): Search everything, trigger agents, quick actions
- **Agent Feed**: Left sidebar shows real-time agent insights streaming in
- **Content Card**: Drag-and-drop scheduling canvas (like Notion x Trello)
- **Analytics Sparklines**: Inline micro-charts everywhere
- **Goal Ring**: iOS-style activity rings for weekly goals

---

## 9. VIDEO EDITOR INTEGRATION

### Strategy: Tiered Approach

| Tier | Tool | Use Case |
|------|------|---------|
| **Basic** (Browser) | Remotion | Programmatic video creation, auto-captions, thumbnail gen |
| **Advanced** (Browser) | FFmpeg.wasm | Trimming, merging, format conversion in browser |
| **Mobile** | FFmpegKit | Native iOS/Android video processing |
| **Pro** (Server-side) | FFmpeg server | Heavy rendering jobs via Celery |
| **AI-powered** | Runway ML API | AI video enhancements, background removal |

### Remotion Integration (Web)

```typescript
// packages/video-editor/components/CaptionedVideo.tsx
import { Composition, Player } from 'remotion';

// Auto-caption reel with niche-branded template
export const CaptionedReel = ({ 
  videoSrc, 
  captions, 
  brandColors,
  niche 
}: ReelProps) => {
  // Render captions with creator's brand colors
  // Add intro/outro templates
  // Generate thumbnail at best frame
};
```

### What the Video Agent Does Automatically:
1. **Upload video** → Auto-transcription (Whisper API, $0.006/min)
2. **Hook detection** → AI identifies strongest 3-second opening
3. **Clip suggestions** → Best 15s, 30s, 60s segments for different platforms
4. **Auto-captions** → Styled to niche brand colors
5. **Thumbnail generation** → Best frame + DALL-E 3 title overlay
6. **B-roll gaps** → Flags talking-head moments > 8 seconds
7. **Music matching** → Suggests trending royalty-free tracks that match energy
8. **Platform resize** → Auto-crop 16:9 → 9:16 for Reels/Shorts

### Free Libraries & Services
- **Whisper** (OpenAI): ~$0.006/min for transcription
- **FFmpeg.wasm**: Free, browser-based, handles most edits
- **Remotion**: Free for small projects (OSS license)
- **FFmpegKit**: Free React Native video processing
- **Pixabay API**: Free stock footage
- **Freesound API**: Free sound effects
- **Jamendo API**: Free/CC music

---

## 10. ANALYTICS SYSTEM

### Real-Time Analytics Pipeline

```
Social Platform Webhooks → FastAPI → Redis Queue → Celery Workers → 
PostgreSQL (partitioned) → Aggregation Layer → Redis Cache → 
GraphQL/REST API → Frontend
```

### Analytics Dashboard Features

#### Overview Dashboard
- Today's stats (views, followers, engagement) vs yesterday
- Best performing post this week
- Follower growth chart (30 days)
- Platform breakdown pie chart
- Goal completion rings

#### Content Performance
- Sortable table: all posts, by engagement, views, date
- Heatmap: which day/hour gets most engagement
- Format comparison: Reels vs Carousels vs Stories
- Hook effectiveness: first 3-second retention chart

#### Audience Intelligence
- Demographic breakdown (age, gender, location)
- Active hours heatmap
- Interests graph
- Top engaged followers

#### Comment Intelligence (Unique Feature)
```
Top Questions This Week (37 found):
1. "What camera do you use?" × 89 times → Create video answering this
2. "How do I start with no budget?" × 67 times → HUGE content opportunity
3. "Can you do X niche video?" × 45 times → Collab request signal

Sentiment Breakdown:
Positive: 78% | Neutral: 15% | Negative: 7%

Negative Cluster: 3 users upset about "product quality in sponsored post"
→ Agent Recommendation: Address this transparently in next video
```

#### Competitor Benchmark
- Your metrics vs top 3 competitors
- Where you're winning / losing
- Gap analysis

---

## 11. SECURITY ARCHITECTURE

### Threat Model & Controls

| Threat | Control |
|--------|---------|
| Account takeover | MFA (TOTP + biometric on mobile), device trust |
| Token theft | AES-256 encrypted OAuth tokens in DB, never in client |
| SQL injection | Parameterized queries, SQLAlchemy ORM, Pydantic validation |
| XSS | CSP headers, React's default escaping, no dangerouslySetInnerHTML |
| CSRF | SameSite=Strict cookies, double-submit cookie pattern |
| Rate limiting | Redis-based per-IP + per-user rate limits on all endpoints |
| DDoS | Cloudflare WAF + rate limiting at edge |
| Data exposure | Row Level Security (Supabase RLS), user can only see their data |
| Scraping abuse | Encrypted tokens, rotating proxies, agent isolation per user |
| Webhook forgery | HMAC signature verification for all platform webhooks |
| Secrets leakage | HashiCorp Vault or Infisical for secrets management |
| Dependency vulnerabilities | Dependabot, Snyk, automated PR security checks |
| Insider access | Zero-trust, all admin actions logged and audited |
| Mobile app reverse engineering | Certificate pinning, code obfuscation (Expo Obfuscator) |
| JWT vulnerabilities | RS256 (asymmetric), short expiry (15min), refresh token rotation |
| Session hijacking | Session binding to device fingerprint |

### OAuth Token Storage
```python
# NEVER store raw OAuth tokens
class TokenEncryptor:
    def __init__(self):
        self.fernet = Fernet(settings.ENCRYPTION_KEY)
    
    def encrypt(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()
```

### API Security Headers
```python
# FastAPI middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    headers={
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'self'...",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
    }
)
```

---

## 12. API DESIGN

### Core Endpoints

```
Authentication:
POST   /v1/auth/register
POST   /v1/auth/login
POST   /v1/auth/refresh
DELETE /v1/auth/logout
POST   /v1/auth/mfa/enable
POST   /v1/auth/mfa/verify

Onboarding:
POST   /v1/onboarding/niches
POST   /v1/onboarding/goals
POST   /v1/onboarding/accounts
POST   /v1/onboarding/competitors
POST   /v1/onboarding/complete

Content:
GET    /v1/content                    ← List with filters
POST   /v1/content                    ← Create
GET    /v1/content/{id}
PATCH  /v1/content/{id}
DELETE /v1/content/{id}
POST   /v1/content/{id}/publish
POST   /v1/content/{id}/schedule
POST   /v1/content/{id}/analyze       ← Trigger virality prediction

Content Ideas:
GET    /v1/ideas                      ← Paginated AI ideas
POST   /v1/ideas/generate             ← Generate new ideas on demand
PATCH  /v1/ideas/{id}/status

Analytics:
GET    /v1/analytics/overview
GET    /v1/analytics/content/{id}
GET    /v1/analytics/accounts/{id}
GET    /v1/analytics/competitors
GET    /v1/analytics/comments/intelligence

Agents:
GET    /v1/agents                     ← List user's agent configs
PATCH  /v1/agents/{type}              ← Update agent config
POST   /v1/agents/{type}/run          ← Trigger manual run
GET    /v1/agents/insights            ← Paginated insights
PATCH  /v1/agents/insights/{id}/read
WS     /v1/ws/agents                  ← Real-time agent stream

Trends:
GET    /v1/trends                     ← Niche-filtered trends
GET    /v1/trends/{id}
POST   /v1/trends/{id}/create-content ← Create content from trend

Competitors:
GET    /v1/competitors
POST   /v1/competitors
DELETE /v1/competitors/{id}
GET    /v1/competitors/{id}/content
GET    /v1/competitors/{id}/analysis

Goals:
GET    /v1/goals
POST   /v1/goals
PATCH  /v1/goals/{id}
DELETE /v1/goals/{id}
GET    /v1/goals/{id}/history

Collaborations:
GET    /v1/collaborations
POST   /v1/collaborations
PATCH  /v1/collaborations/{id}
POST   /v1/collaborations/{id}/contract/generate
POST   /v1/collaborations/{id}/contract/send

Inbox:
GET    /v1/inbox                      ← All DMs with AI classification
GET    /v1/inbox/{id}
POST   /v1/inbox/{id}/reply
PATCH  /v1/inbox/{id}/link-collab

Schedule:
GET    /v1/schedule                   ← Calendar view
POST   /v1/schedule/optimize          ← AI optimize posting times
GET    /v1/schedule/queue             ← Queued posts

News:
GET    /v1/news                       ← Personalized news feed
GET    /v1/news/{id}
POST   /v1/news/{id}/create-content

Media:
POST   /v1/media/upload               ← Presigned URL upload to R2
POST   /v1/media/process-video        ← Trigger video agent
GET    /v1/media                      ← Media library

Webhooks (inbound from platforms):
POST   /webhooks/instagram
POST   /webhooks/youtube
POST   /webhooks/tiktok
POST   /webhooks/twitter
```

---

## 13. DEPLOYMENT & INFRASTRUCTURE

### Production Setup

```yaml
# docker-compose.prod.yml
services:
  api:
    image: contentflow-api:latest
    replicas: 3
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - REDIS_URL=redis://redis:6379
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    
  celery-default:
    image: contentflow-api:latest
    command: celery -A app.workers worker -Q default -c 4
    
  celery-agents:
    image: contentflow-api:latest
    command: celery -A app.workers worker -Q agents -c 8
    # Separate queue for agent tasks
    
  celery-scrapers:
    image: contentflow-api:latest
    command: celery -A app.workers worker -Q scrapers -c 2
    # Scrapers need lower concurrency, more memory
    
  celery-beat:
    image: contentflow-api:latest
    command: celery -A app.workers beat
    # Scheduler for periodic agent runs
    
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
      
  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
      
  meilisearch:
    image: getmeili/meilisearch:latest
    volumes:
      - meilisearch_data:/meili_data
      
  playwright:
    image: contentflow-scraper:latest
    # Dedicated scraper service with Playwright
```

### Monitoring Stack

```
Prometheus (metrics collection)
    ↓
Grafana (dashboards)
    ↓
Alertmanager (PagerDuty/Slack alerts)

Loki (log aggregation)
    ↓
Grafana (log search)

Sentry (error tracking, frontend + backend)
PostHog (product analytics, self-hosted)
```

### Key Metrics to Monitor
- Agent run success rate by type
- Agent execution time (p50, p95, p99)
- API response times
- Celery queue depth per queue
- LLM API costs per user per day
- Social platform API rate limit utilization
- Content publish success rate
- WebSocket connection count

---

## 14. MOBILE STRATEGY

### Expo App Structure

```
apps/mobile/
├── app/
│   ├── (auth)/
│   │   ├── login.tsx
│   │   └── onboarding/
│   ├── (tabs)/
│   │   ├── index.tsx          ← Home / Command Center
│   │   ├── create.tsx         ← Content creator
│   │   ├── insights.tsx       ← Agent insights
│   │   ├── analytics.tsx      ← Stats
│   │   └── inbox.tsx          ← DM inbox
│   └── modals/
│       ├── content-idea.tsx
│       └── goal-setup.tsx
├── components/
│   ├── AgentFeed.tsx
│   ├── ContentCard.tsx
│   ├── GoalRings.tsx
│   └── TrendCard.tsx
```

### Mobile-Specific Features
- **Push Notifications**: Goal reminders, trend alerts, collab inquiries
- **Widget Support**: Today's stats on home screen (iOS 16+/Android)
- **Quick Capture**: One-tap to record + AI analyzes and suggests caption
- **Face ID/Touch ID**: Biometric login
- **Offline Mode**: Draft content offline, sync when connected
- **In-App Browser**: Preview posts before publishing
- **Haptic Feedback**: Satisfying feedback on goal milestones

### OTA Updates (No App Store Wait)
```bash
# Deploy update to all mobile users instantly
eas update --branch production --message "Agent UX improvements"
# Users get update in background, no app store review needed
# (within Expo policy limits — can't change native modules)
```

---

## 15. DEVELOPMENT ROADMAP

### Phase 1 — Foundation (Weeks 1-6)
**Goal**: Core app running, first 3 agents live, publishable MVP

- [ ] Monorepo setup (Turborepo)
- [ ] FastAPI backend scaffold with auth, user model, social accounts
- [ ] Next.js frontend with auth, onboarding flow (niche selection)
- [ ] PostgreSQL schema (full schema above)
- [ ] Social platform OAuth (Instagram, YouTube, TikTok priority)
- [ ] Basic content scheduling and posting
- [ ] Trend Detection Agent (most impactful, fastest to build)
- [ ] Goal & Accountability Agent
- [ ] Analytics Agent (fetch + display)
- [ ] Basic analytics dashboard

### Phase 2 — Intelligence Layer (Weeks 7-12)
**Goal**: Agents become genuinely useful, creators want to use it daily

- [ ] Competitor Intelligence Agent
- [ ] Content Research & Ideation Agent
- [ ] News & Research Agent
- [ ] Niche Intelligence Agent with Qdrant
- [ ] Comment Intelligence feature
- [ ] Smart Scheduling Agent
- [ ] Agent insights feed with WebSocket
- [ ] Video Intelligence Agent (upload + transcribe + clip)
- [ ] Basic video editor (FFmpeg.wasm)
- [ ] Expo mobile app (feature parity with web for key flows)

### Phase 3 — Business Layer (Weeks 13-18)
**Goal**: Become indispensable for creator's income

- [ ] Collaboration & Business Agent
- [ ] DM inbox classification
- [ ] Contract generation
- [ ] Predictive Virality Agent
- [ ] Growth & Engagement Agent
- [ ] Tips & Tricks Agent
- [ ] Full video editor (Remotion integration)
- [ ] Platform expansion (LinkedIn, Pinterest, Facebook)
- [ ] Mobile push notifications + widgets

### Phase 4 — Scale & Monetize (Weeks 19-24)
**Goal**: Launch publicly, acquire first 1000 paying users

- [x] Payment integration (Stripe) ✅ **COMPLETED - Phase 11**
- [x] Subscription tiers (Free/Pro/Business) ✅ **COMPLETED - Phase 11**
- [ ] App Store submissions (iOS + Android)
- [ ] API cost optimization (smart caching, model selection)
- [ ] Performance optimization (CDN, edge caching)
- [ ] Creator community features
- [ ] Referral program
- [ ] Public launch

**Phase 11 Status**: ✅ **PRODUCTION READY**
- Stripe billing fully integrated
- Database schema updated with billing columns
- Webhook handling implemented
- Entitlement system active
- Celery reconciliation tasks created
- See `PHASE_11_IMPLEMENTATION_COMPLETE.md` for details

---

## 16. REVENUE MODEL

### Subscription Tiers

| Feature | Free | Pro ($29/mo) | Business ($79/mo) |
|---------|------|-------------|-------------------|
| Connected accounts | 2 | 6 | Unlimited |
| AI agents | 3 basic | All 14 | All 14 + custom |
| Content ideas/mo | 30 | Unlimited | Unlimited |
| Competitor tracking | 2 | 10 | 50 |
| Agent runs/day | 10 | 200 | Unlimited |
| Video processing | 5 videos/mo | 50 videos/mo | Unlimited |
| Analytics history | 30 days | 1 year | 3 years |
| Team members | 1 | 1 | 5 |
| Collaboration pipeline | Basic | Full | Full + CRM |
| API access | ❌ | ❌ | ✅ |
| White-label | ❌ | ❌ | ✅ |

### Additional Revenue
- **Marketplace**: Sell proven content templates between creators (15% commission)
- **Affiliate**: Brand discovery marketplace for creators seeking deals
- **Agency Plan**: $299/mo for agencies managing multiple creator accounts

---

## FINAL NOTES

### What Makes This Win

1. **Niche-first = feels like it was built for you.** Buffer feels generic. ContentFlow feels personal.
2. **Agents do real work.** Not just chatbots — they run, fetch, analyze, and alert automatically.
3. **Business pipeline.** No other tool turns DMs into tracked, contracted deals.
4. **Goal accountability.** Creators struggle with consistency. A digital coach changes behavior.
5. **Competitor intelligence.** Knowing what works for competitors = unfair advantage.
6. **One app for everything.** Creating, publishing, analytics, business — all in one.

### Critical Success Factors
- Agent reliability > Agent sophistication. An agent that runs perfectly every time beats a smarter one that sometimes fails.
- Mobile push notifications are your retention tool. Use them wisely.
- The onboarding niche selection experience must be magical. First impression = retention.
- Start with 3 platforms (Instagram, YouTube, TikTok). Do them perfectly before expanding.
- Cost control on LLM calls is existential. Cache aggressively, use smaller models where possible.

---

*Document generated for ContentFlow AI Platform | Architecture Version 1.0*
*Review quarterly as tech landscape evolves*