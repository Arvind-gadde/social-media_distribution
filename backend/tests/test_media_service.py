import pytest
import io
from unittest.mock import AsyncMock, patch
from fastapi import UploadFile
from app.services.media_service import MediaService
from app.exceptions import MediaError, StorageError

@pytest.fixture
def media_service():
    return MediaService()

def mock_upload_file(filename, content_type, size, content=b"fake data"):
    file_mock = AsyncMock(spec=UploadFile)
    file_mock.filename = filename
    file_mock.content_type = content_type
    file_mock.size = size
    
    async def side_effect(*args, **kwargs):
        if not hasattr(file_mock, "_read_once"):
            file_mock._read_once = True
            return content
        return b""
    
    file_mock.read.side_effect = side_effect
    return file_mock

def test_validate_success(media_service):
    file = mock_upload_file("test.jpg", "image/jpeg", 1024)
    media_service.validate(file)

def test_validate_missing_filename(media_service):
    file = mock_upload_file("", "image/jpeg", 1024)
    with pytest.raises(MediaError, match="Filename is required"):
        media_service.validate(file)

def test_validate_missing_ext(media_service):
    file = mock_upload_file("test", "image/jpeg", 1024)
    with pytest.raises(MediaError, match="must have an extension"):
        media_service.validate(file)

def test_validate_bad_mime(media_service):
    file = mock_upload_file("test.exe", "application/x-msdownload", 1024)
    with pytest.raises(MediaError, match="is not allowed"):
        media_service.validate(file)

@patch("app.services.media_service.MAX_UPLOAD_SIZE_BYTES", 500)
def test_validate_too_large(media_service):
    file = mock_upload_file("test.jpg", "image/jpeg", 1024)
    with pytest.raises(MediaError, match="too large"):
        media_service.validate(file)

def test_detect_media_type(media_service):
    assert media_service.detect_media_type("image/png") == "image"
    assert media_service.detect_media_type("video/mp4") == "video"
    assert media_service.detect_media_type("application/json") == "text"

@pytest.fixture
def mock_s3():
    with patch("app.services.media_service.aiobotocore.session.get_session") as get_session_mock:
        session_mock = get_session_mock.return_value
        client_mock = AsyncMock()
        class ClientContextManager:
            async def __aenter__(self):
                return client_mock
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        session_mock.create_client.return_value = ClientContextManager()
        yield client_mock

@patch("app.services.media_service.uuid.uuid4")
@pytest.mark.asyncio
async def test_upload_success(mock_uuid, mock_s3, media_service):
    mock_uuid.return_value.hex = "fake-uuid"
    file = mock_upload_file("test.jpg", "image/jpeg", 1024, b"image data")
    
    key, url = await media_service.upload(file, "user_1")
    
    assert key == "media/user_1/fake-uuid.jpg"
    assert "fake-uuid.jpg" in url
    mock_s3.put_object.assert_called_once()
    assert mock_s3.put_object.call_args[1]["Key"] == key
    assert mock_s3.put_object.call_args[1]["Body"] == b"image data"

@patch("app.services.media_service.MAX_UPLOAD_SIZE_BYTES", 5)
@pytest.mark.asyncio
async def test_upload_streaming_size_limit(mock_s3, media_service):
    file = mock_upload_file("test.jpg", "image/jpeg", None, b"long content > 5 bytes")
    with pytest.raises(MediaError, match="exceeded maximum size"):
        await media_service.upload(file, "user_1")

@pytest.mark.asyncio
async def test_upload_storage_error(mock_s3, media_service):
    mock_s3.put_object.side_effect = Exception("S3 down")
    file = mock_upload_file("test.jpg", "image/jpeg", 1024, b"data")
    
    with pytest.raises(StorageError, match="Failed to upload media"):
        await media_service.upload(file, "user_1")

@pytest.mark.asyncio
async def test_delete_success(mock_s3, media_service):
    await media_service.delete("media/key.jpg")
    mock_s3.delete_object.assert_called_once()
    assert mock_s3.delete_object.call_args[1]["Key"] == "media/key.jpg"

@pytest.mark.asyncio
async def test_delete_empty_key(mock_s3, media_service):
    await media_service.delete("")
    mock_s3.delete_object.assert_not_called()

@pytest.mark.asyncio
async def test_delete_failure_swallowed(mock_s3, media_service):
    mock_s3.delete_object.side_effect = Exception("error")
    await media_service.delete("media/key.jpg")
