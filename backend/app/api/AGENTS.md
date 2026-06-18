# Backend Rules — FastAPI (Python 3.12, Pydantic v2, SQLAlchemy 2.0 async)

## PYDANTIC V2 — NEVER USE V1 SYNTAX
```python
# CORRECT (v2)
class ContentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str | None = None

# WRONG — breaks silently with v2
class ContentItemResponse(BaseModel):
    class Config:
        orm_mode = True  # ← v1 syntax, will NOT work
```

## SQLALCHEMY 2.0 — USE THE NEW API
```python
# CORRECT
from sqlalchemy import select, update, delete
result = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()

# WRONG — legacy query API
user = db.query(User).filter(User.id == user_id).first()  # not async-compatible
```

## CELERY TASK PATTERN
```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="agents",           # always specify queue explicitly
    name="agents.task_name",  # always name explicitly — never use auto-generated names
)
def my_task(self, user_id: str):
    try:
        pass  # task logic
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

## STRUCTLOG — ALWAYS STRUCTURED LOGGING
```python
import structlog
log = structlog.get_logger()

# CORRECT — structured, searchable
log.info("content.published", content_id=str(item.id), user_id=str(user.id), platform=platform)

# WRONG — unstructured, unsearchable
log.info(f"Content {item.id} published by {user.id}")
```

## RATE LIMITING — ALL PUBLIC ENDPOINTS
```python
from app.middleware.rate_limit import rate_limit

@router.post("/content", dependencies=[Depends(rate_limit(requests=10, window=60))])
async def create_content(...):
    ...
```

## TOKEN ENCRYPTION — ALWAYS ENCRYPT OAUTH TOKENS
```python
from app.utils.crypto import TokenEncryptor
encryptor = TokenEncryptor()

# Before saving to DB
encrypted = encryptor.encrypt(raw_oauth_token)

# After reading from DB
raw = encryptor.decrypt(db_token)
```

## WEBSOCKET — AGENT EVENT STREAMING PATTERN
```python
# Agents publish to Redis pub/sub
await redis.publish(f"user:{user_id}:agent_events", json.dumps({
    "type": "agent_insight",
    "agent": "trend_detection",
    "priority": 9,
    "title": "Trend alert title",
    "body": "Details...",
}))
# Frontend WebSocket handler picks this up and streams to client
```