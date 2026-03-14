# ContentFlow India 🚀

Multi-platform social media content distribution for Indian creators.
Upload once → reach 12+ platforms simultaneously.

## Platforms Supported
Instagram · YouTube · YouTube Shorts · Facebook · LinkedIn · X/Twitter
Josh · Moj · ShareChat · Koo · Chingari · Roposo

## Quick Start

```bash
# 1. Copy env files
cp backend/.env.example backend/.env
# Fill in your API keys

# 2. Start all services
docker-compose up -d

# 3. Run DB migrations
docker-compose exec backend alembic upgrade head

# 4. Open app
open http://localhost
```

## Architecture

- **FastAPI** — async REST API with dependency injection
- **SQLAlchemy 2.0** — async ORM with typed models
- **Celery + Redis** — background task queue for platform distribution
- **MinIO** — S3-compatible object storage (swap for AWS S3 in production)
- **PostgreSQL** — primary database with Alembic migrations
- **React + TypeScript + Tailwind** — frontend

## Security Highlights
- Platform OAuth tokens encrypted at rest (Fernet)
- Auth via HttpOnly cookies — no tokens in localStorage
- JWT with JTI blacklisting on logout
- OAuth CSRF protection with state parameter
- Input validation at every boundary

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v --cov=app
```
