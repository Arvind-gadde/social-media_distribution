# ContentFlow India 🚀

**AI-powered multi-platform social media content distribution and content intelligence platform for Indian creators.**

Upload once → reach 12+ platforms simultaneously with AI-generated, platform-optimized content.

## 🌟 Key Features

### Multi-Platform Distribution
Upload content once and distribute across **12+ platforms** simultaneously:
- **Global Platforms**: Instagram, YouTube (including Shorts), Facebook, LinkedIn, X/Twitter
- **Indian Platforms**: Josh, Moj, ShareChat, Koo, Chingari, Roposo

### AI Content Intelligence
- **Multi-Agent Pipeline**: Automated content collection, analysis, and generation
  - **Scout**: Collects content from 50+ free sources (YouTube, GitHub, arXiv, news APIs)
  - **Analyst**: Identifies virality signals, value gaps, and trending topics
  - **Fact-Checker**: Verifies claims and flags disputed information
  - **Creative Agent**: Generates platform-specific content (hooks, captions, scripts, threads)
- **Platform Optimization**: AI generates content tailored to each platform's character limits and audience
- **Regional Language Support**: Content generation in Hindi, Tamil, Telugu, Bengali, Marathi, and Gujarati

### Content Insights Dashboard
- **Virality Scoring**: Predictive scoring based on cross-source signals and trend velocity
- **Value Gap Detection**: Identifies underexplored angles and unique content opportunities
- **Sentiment Analysis**: Real-time sentiment breakdown (positive/negative/controversial)
- **Pipeline Health Monitoring**: Track AI agent performance with detailed metrics

### Security & Privacy
- Platform OAuth tokens encrypted at rest (Fernet encryption)
- Authentication via HttpOnly cookies — no tokens in localStorage
- JWT with JTI blacklisting on logout
- OAuth CSRF protection with state parameter
- Input validation at every boundary

## 🏗️ Architecture

### Backend
- **FastAPI** — Async REST API with dependency injection
- **SQLAlchemy 2.0** — Async ORM with typed models
- **Celery + Redis** — Background task queue for platform distribution and AI agent pipeline
- **PostgreSQL** — Primary database with Alembic migrations
- **MinIO** — S3-compatible object storage (swappable for AWS S3 in production)
- **AI Integration**: Google Gemini, OpenAI GPT-4o-mini with automatic fallback

### Frontend
- **React 18** + **TypeScript** — Type-safe UI components
- **Tailwind CSS** — Utility-first styling with custom glassmorphism design
- **Vite** — Fast HMR and optimized builds
- **TanStack Query** — Server state management
- **Zustand** — Lightweight state management
- **React Router v6** — Client-side routing

### Infrastructure
- **Docker Compose** — One-command local development
- **Nginx** — Reverse proxy and static file serving
- **Redis** — Cache layer and Celery message broker

## 📊 Supported AI Capabilities

### Content Generation
- **Instagram**: Captions, hooks, hashtags (up to 2200 chars)
- **YouTube Scripts**: Full video outlines with engagement tips
- **Twitter Threads**: Multi-tweet threads with copy-friendly format
- **LinkedIn Posts**: Professional content with engagement strategies
- **Regional Platforms**: Optimized content for Josh, Moj, Koo, etc.

### Content Analysis
- **Virality Prediction**: Score based on cross-source mentions and trend velocity
- **Sentiment Breakdown**: Positive/negative/controversial analysis
- **Fact-Checking**: Claim verification with confidence scores
- **B-Roll Suggestions**: Asset recommendations from GitHub, YouTube, arXiv

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development without Docker)
- Node.js 18+ (for local frontend development)

### Getting Started

```bash
# 1. Clone and setup environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your API keys (see Configuration section)

# 2. Start all services
docker-compose up -d

# 3. Run database migrations (usually automatic on startup)
docker-compose exec backend alembic upgrade head

# 4. Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# MinIO Console: http://localhost:9001
```

### DEV Mode (No Auth Required)
In development, authentication is bypassed by default. A dev user is automatically created:
- Email: `dev@local.dev`
- No login required — just open the app

## 🔧 Configuration

### Required API Keys

| Service | Environment Variable | Purpose |
|---------|---------------------|---------|
| Google Gemini | `GEMINI_API_KEY` | Free tier: 1,500 req/day for caption generation |
| OpenAI | `OPENAI_API_KEY` | Fallback for GPT-4o-mini |
| YouTube Data | `YOUTUBE_API_KEY` | Content collection from YouTube |
| Google OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google login |
| Platform OAuth | Various (see `.env.example`) | Instagram, Facebook, LinkedIn, Twitter, etc. |

### Generate Required Keys

```bash
# Fernet encryption key for token encryption
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# JWT secret
openssl rand -hex 64

# VAPID keys for web push
python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print('Private:', v.private_key); print('Public:', v.public_key)"
```

## 🧪 Running Tests

```bash
# With Docker
docker-compose exec backend pytest tests/ -v --cov=app

# Locally
cd backend
pip install -r requirements.txt
pytest tests/ -v --cov=app
```

## 📁 Project Structure

```
contentflow/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints
│   │   │   ├── auth.py      # Authentication & OAuth
│   │   │   ├── posts.py     # Content management
│   │   │   ├── ai.py        # AI generation endpoints
│   │   │   ├── analytics.py # Platform analytics
│   │   │   ├── agent.py     # Content agent feed
│   │   │   └── insights.py  # Intelligence dashboard
│   │   ├── core/            # Middleware, logging, security
│   │   ├── db/              # Database session management
│   │   ├── models/          # SQLAlchemy models
│   │   ├── repositories/    # Data access layer
│   │   ├── schemas/         # Pydantic validation
│   │   ├── services/        # Business logic
│   │   │   ├── content_agent/  # Multi-agent AI pipeline
│   │   │   │   ├── orchestrator.py
│   │   │   │   ├── collector.py
│   │   │   │   ├── analyst_agent.py
│   │   │   │   ├── fact_checker.py
│   │   │   │   └── creative_agent.py
│   │   │   └── platforms/   # Platform integrations
│   │   └── workers/         # Celery tasks
│   └── alembic/             # Database migrations
├── frontend/
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # UI components
│   │   ├── pages/           # Route pages
│   │   ├── store/           # Zustand stores
│   │   └── types/           # TypeScript types
│   └── public/
└── nginx/                   # Nginx configuration
```

## 🔐 Security Features

- **Token Encryption**: Fernet encryption for all platform OAuth tokens
- **HttpOnly Cookies**: JWT stored in HttpOnly cookies (not localStorage)
- **JWT Blacklisting**: JTI-based token revocation on logout
- **Rate Limiting**: Per-endpoint rate limits (login: 5/min, upload: 10/min)
- **CORS Protection**: Configurable allowed origins
- **Input Validation**: Pydantic schemas at every API boundary
- **SQL Injection Prevention**: SQLAlchemy parameterized queries
- **XSS Protection**: Content Security Policy headers

## 📈 Analytics & Monitoring

### Agent Pipeline Metrics
- Items fetched, new items, scored items
- Fact-check pass/fail rates
- Content generation counts
- Stage timing (scout, analyst, checker, creative)
- Error tracking per stage

### Platform Analytics
- Per-platform engagement metrics
- Post performance tracking
- Audience growth analytics
- Best posting time recommendations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with FastAPI, React, and Tailwind CSS
- AI powered by Google Gemini and OpenAI
- Indian creator-focused design

---

**Made with ❤️ for Indian creators**
