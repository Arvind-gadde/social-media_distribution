import pytest
from unittest.mock import AsyncMock, patch
from app.services.compression_service import compress_video_for_platform, get_video_info
from app.exceptions import MediaError

@pytest.fixture
def mock_subprocess():
    with patch("app.services.compression_service.asyncio.create_subprocess_exec") as mock_exec:
        process_mock = AsyncMock()
        process_mock.communicate = AsyncMock(return_value=(b"", b""))
        process_mock.returncode = 0
        mock_exec.return_value = process_mock
        yield process_mock, mock_exec

@patch("app.services.compression_service.PLATFORM_VIDEO_SPECS", {"twitter": {"fps": 30, "resolution": "1280x720", "max_size_mb": 512, "max_duration_s": 140}})
@pytest.mark.asyncio
async def test_compress_video_success(mock_subprocess):
    process_mock, mock_exec = mock_subprocess
    
    output_path = await compress_video_for_platform("input.mp4", "twitter")
    
    assert "twitter.mp4" in output_path
    mock_exec.assert_called_once()
    cmd_called = mock_exec.call_args[0]
    assert "ffmpeg" in cmd_called
    assert "-i" in cmd_called
    assert "input.mp4" in cmd_called
    # check that spec arguments are correctly formatted in command
    assert "-r" in cmd_called
    assert "30" in cmd_called
    assert "-t" in cmd_called
    assert "140" in cmd_called

@pytest.mark.asyncio
async def test_compress_video_failure(mock_subprocess):
    process_mock, mock_exec = mock_subprocess
    process_mock.returncode = 1
    process_mock.communicate = AsyncMock(return_value=(b"", b"ffmpeg error output"))
    
    with pytest.raises(MediaError) as exc_info:
        await compress_video_for_platform("input.mp4", "unknown_platform")
    
    assert "ffmpeg error output" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_video_info_success(mock_subprocess):
    process_mock, mock_exec = mock_subprocess
    
    mock_ffprobe_output = b'{"format": {"duration": "10.5", "size": "1048576"}, "streams": [{"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30000/1001"}]}'
    process_mock.communicate = AsyncMock(return_value=(mock_ffprobe_output, b""))
    
    info = await get_video_info("video.mp4")
    assert info["duration"] == 10.5
    assert info["size_mb"] == 1.0  # 1048576 bytes = 1MB
    assert info["width"] == 1920
    assert info["height"] == 1080
    assert info["fps"] == 29.97

@pytest.mark.asyncio
async def test_get_video_info_parse_error(mock_subprocess):
    process_mock, mock_exec = mock_subprocess
    process_mock.communicate = AsyncMock(return_value=(b"invalid json format", b""))
    
    info = await get_video_info("video.mp4")
    assert info == {"duration": 0, "size_mb": 0, "width": None, "height": None, "fps": 0}

@pytest.mark.asyncio
async def test_get_video_info_ffprobe_fail(mock_subprocess):
    process_mock, mock_exec = mock_subprocess
    process_mock.returncode = 1
    process_mock.communicate = AsyncMock(return_value=(b"", b"ffprobe error logs"))
    
    info = await get_video_info("video.mp4")
    assert info == {"duration": 0, "size_mb": 0, "width": None, "height": None, "fps": 0}

@pytest.mark.asyncio
async def test_get_video_info_malformed_r_frame_rate(mock_subprocess):
    process_mock, mock_exec = mock_subprocess
    mock_ffprobe_output = b'{"format": {"duration": "1", "size": "1"}, "streams": [{"codec_type": "video", "r_frame_rate": "malformed_string"}]}'
    process_mock.communicate = AsyncMock(return_value=(mock_ffprobe_output, b""))
    
    info = await get_video_info("video.mp4")
    assert info["fps"] == 0 # Caught gracefully
