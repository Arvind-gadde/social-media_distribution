"""Video compression service — wraps ffmpeg for per-platform specs."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import structlog

from app.constants import PLATFORM_VIDEO_SPECS
from app.exceptions import MediaError

logger = structlog.get_logger(__name__)

_OUTPUT_DIR = Path("/tmp/contentflow/compressed")


async def compress_video_for_platform(
    input_path: str,
    platform: str,
) -> str:
    """
    Compress a video to meet the given platform's specs.
    Returns a local path to the compressed file.
    Raises MediaError if ffmpeg fails.
    """
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    specs = PLATFORM_VIDEO_SPECS.get(platform, {})
    output_path = _OUTPUT_DIR / f"{uuid.uuid4().hex}_{platform}.mp4"

    cmd = ["ffmpeg", "-i", input_path, "-y", "-c:v", "libx264",
           "-preset", "fast", "-crf", "28", "-c:a", "aac", "-b:a", "128k"]

    if specs.get("resolution"):
        w, h = specs["resolution"].split("x")
        cmd += [
            "-vf",
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black",
        ]

    if specs.get("fps"):
        cmd += ["-r", str(specs["fps"])]

    if specs.get("max_duration_s"):
        cmd += ["-t", str(specs["max_duration_s"])]

    if specs.get("max_size_mb"):
        # Estimate bitrate for a 60s video to stay under max size
        target_kbps = min(int(specs["max_size_mb"] * 8 * 1024 / 60), 4000)
        cmd += ["-b:v", f"{target_kbps}k"]

    cmd.append(str(output_path))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode()[:500]
        logger.error("ffmpeg_failed", platform=platform, stderr=error_msg)
        raise MediaError(f"Video compression failed for {platform}: {error_msg}")

    logger.info("video_compressed", platform=platform, output=str(output_path))
    return str(output_path)


async def get_video_info(file_path: str) -> dict:
    """Return duration, size, width, height, fps via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        file_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()

    if process.returncode != 0:
        return {"duration": 0, "size_mb": 0, "width": None, "height": None, "fps": 0}

    try:
        info = json.loads(stdout.decode())
        video_stream = next(
            (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        fps_raw = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = fps_raw.split("/")
            fps = float(num) / float(den) if float(den) else 0
        except Exception:
            fps = 0

        return {
            "duration": float(info.get("format", {}).get("duration", 0)),
            "size_mb": int(info.get("format", {}).get("size", 0)) / (1024 * 1024),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": round(fps, 2),
        }
    except Exception as exc:
        logger.warning("ffprobe_parse_failed", error=str(exc))
        return {"duration": 0, "size_mb": 0, "width": None, "height": None, "fps": 0}
