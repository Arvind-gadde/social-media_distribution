"""MFA / TOTP enrollment + verification endpoints."""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.services import mfa_service

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth/mfa", tags=["auth", "mfa"])


class EnrollResponse(BaseModel):
    secret: str
    provisioning_uri: str
    backup_codes: list[str]


class VerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=12)


class StatusResponse(BaseModel):
    enabled: bool
    backup_codes_remaining: int


@router.get("/status", response_model=StatusResponse)
async def mfa_status(current_user: Annotated[User, Depends(get_current_user)]):
    return StatusResponse(
        enabled=bool(current_user.mfa_enabled),
        backup_codes_remaining=len(current_user.mfa_backup_codes or []),
    )


@router.post("/enroll", response_model=EnrollResponse)
async def mfa_enroll(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Begin enrollment — stores a pending secret on the user; not yet enabled.

    Caller must POST /verify with a valid code to flip ``mfa_enabled`` to True.
    """
    pkg = mfa_service.start_enrollment(account_name=current_user.email)
    current_user.mfa_secret = pkg.secret
    current_user.mfa_enabled = False
    current_user.mfa_backup_codes = pkg.backup_codes
    await db.flush()
    await db.commit()
    log.info("mfa_enrollment_started", user_id=str(current_user.id))
    return EnrollResponse(
        secret=pkg.secret,
        provisioning_uri=pkg.provisioning_uri,
        backup_codes=pkg.backup_codes,
    )


@router.post("/verify")
async def mfa_verify(
    request: VerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Verify the supplied TOTP code; flip ``mfa_enabled`` on first success."""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not enrolled")
    if not mfa_service.verify_totp(current_user.mfa_secret, request.code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    just_enabled = not current_user.mfa_enabled
    current_user.mfa_enabled = True
    await db.flush()
    await db.commit()
    log.info("mfa_verified", user_id=str(current_user.id), just_enabled=just_enabled)
    return {"ok": True, "just_enabled": just_enabled}


@router.post("/disable")
async def mfa_disable(
    request: VerifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Disable MFA. Requires a fresh TOTP code or backup code."""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not enabled")
    ok = mfa_service.verify_totp(current_user.mfa_secret or "", request.code)
    if not ok:
        consumed, remaining = mfa_service.consume_backup_code(
            current_user.mfa_backup_codes, request.code
        )
        if not consumed:
            raise HTTPException(status_code=401, detail="Invalid code")
        current_user.mfa_backup_codes = remaining

    current_user.mfa_secret = None
    current_user.mfa_enabled = False
    current_user.mfa_backup_codes = []
    await db.flush()
    await db.commit()
    log.info("mfa_disabled", user_id=str(current_user.id))
    return {"ok": True}


@router.post("/backup/regenerate", response_model=EnrollResponse)
async def regenerate_backup_codes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA must be enabled first")
    codes = mfa_service.generate_backup_codes()
    current_user.mfa_backup_codes = codes
    await db.flush()
    await db.commit()
    return EnrollResponse(
        secret=current_user.mfa_secret,
        provisioning_uri=mfa_service.build_provisioning_uri(
            current_user.mfa_secret, account_name=current_user.email
        ),
        backup_codes=codes,
    )
