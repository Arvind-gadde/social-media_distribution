"""LinkedIn platform service."""

from __future__ import annotations

import httpx

from app.services.platforms.base import BasePlatformService
from app.exceptions import PlatformError

_BASE = "https://api.linkedin.com/v2"
_MAX_TEXT = 3_000


class LinkedInService(BasePlatformService):
    platform_name = "linkedin"

    def __init__(self, access_token: str, person_urn: str) -> None:
        self._token = access_token
        self._urn = person_urn
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def post_text(self, text: str) -> dict:
        payload = {
            "author": f"urn:li:person:{self._urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text[:_MAX_TEXT]},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                return await self._post_with_retry(
                    client, f"{_BASE}/ugcPosts", headers=self._headers, json=payload
                )
            except Exception as exc:
                raise self._wrap_error(exc, "post_text")

    async def post_image(self, image_url: str, caption: str) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Step 1: Register upload
                reg = await self._post_with_retry(
                    client,
                    f"{_BASE}/assets?action=registerUpload",
                    headers=self._headers,
                    json={
                        "registerUploadRequest": {
                            "owner": f"urn:li:person:{self._urn}",
                            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                            "serviceRelationships": [{
                                "identifier": "urn:li:userGeneratedContent",
                                "relationshipType": "OWNER",
                            }],
                        }
                    },
                )
                upload_mechanism = reg["value"]["uploadMechanism"]
                upload_url = upload_mechanism[
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
                ]["uploadUrl"]
                asset = reg["value"]["asset"]

                # Step 2: Upload image bytes
                image_bytes = (await client.get(image_url)).content
                await client.put(
                    upload_url,
                    content=image_bytes,
                    headers={"Authorization": f"Bearer {self._token}"},
                )

                # Step 3: Create post
                payload = {
                    "author": f"urn:li:person:{self._urn}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": caption[:_MAX_TEXT]},
                            "shareMediaCategory": "IMAGE",
                            "media": [{"status": "READY", "media": asset}],
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                }
                return await self._post_with_retry(
                    client, f"{_BASE}/ugcPosts", headers=self._headers, json=payload
                )
            except PlatformError:
                raise
            except Exception as exc:
                raise self._wrap_error(exc, "post_image")
