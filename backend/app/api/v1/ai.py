"""AI routes — caption generation and hashtag suggestions."""
from __future__ import annotations
from fastapi import APIRouter
from app.api.deps import AISvc, CurrentUser
from app.schemas.schemas import AICaptionRequest, AICaptionResponse, HashtagResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate-caption", response_model=AICaptionResponse)
async def generate_caption(
    req: AICaptionRequest, _: CurrentUser, ai_service: AISvc
) -> AICaptionResponse:
    caption = await ai_service.generate_caption(
        topic=req.topic,
        tone=req.tone,
        language=req.language,
        media_type=req.media_type,
        platforms=req.platforms,
    )
    return AICaptionResponse(caption=caption)


@router.post("/suggest-hashtags", response_model=HashtagResponse)
async def suggest_hashtags(
    platform: str, caption: str, language: str = "en",
    _: CurrentUser = None, ai_service: AISvc = None,
) -> HashtagResponse:
    hashtags = await ai_service.suggest_hashtags(platform, caption, language)
    return HashtagResponse(hashtags=hashtags)
