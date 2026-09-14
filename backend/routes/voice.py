from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    status,
)
from typing import Optional, List, Dict, Any
import tempfile
import os
import asyncio
import base64
import binascii
from datetime import datetime
import logging

from ai_models.whisper_client import whisper


logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# CONFIGURATION
# ============================================================

SUPPORTED_FORMATS = [
    ".webm",
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".flac",
]

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
MAX_BATCH_FILES = 10
DEFAULT_BASE64_FORMAT = "webm"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def transcribe_audio_async(audio_path: str) -> str:
    """
    Run the synchronous Whisper transcription function in a
    worker thread so the FastAPI event loop is not blocked.
    """

    if whisper is None:
        raise RuntimeError(
            "Whisper service is not available"
        )

    return await asyncio.to_thread(
        whisper.transcribe,
        audio_path,
    )


def validate_audio_format(filename: Optional[str]) -> bool:
    """
    Check whether the uploaded filename has a supported
    audio extension.
    """

    if not filename:
        return False

    filename = os.path.basename(filename)

    _, extension = os.path.splitext(filename)

    return extension.lower() in SUPPORTED_FORMATS


def get_audio_extension(filename: Optional[str]) -> str:
    """Return a normalized audio extension."""

    if not filename:
        return ""

    filename = os.path.basename(filename)

    _, extension = os.path.splitext(filename)

    return extension.lower()


def get_audio_duration(file_path: str) -> float:
    """
    Get audio duration.

    WAV files can be read directly using Python's wave module.
    Other formats are handled by Whisper/ffmpeg internally.
    """

    if not file_path:
        return 0.0

    try:
        if file_path.lower().endswith(".wav"):
            import wave

            with wave.open(file_path, "rb") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()

                if rate <= 0:
                    return 0.0

                return frames / float(rate)

    except Exception as exc:
        logger.debug(
            "Could not determine audio duration: %s",
            exc,
        )

    return 0.0


def decode_base64_audio(base64_str: str) -> bytes:
    """
    Decode Base64 audio safely.

    Supports both:
        raw Base64
    and:
        data:audio/webm;base64,...
    """

    if not isinstance(base64_str, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio data must be a Base64 string",
        )

    base64_str = base64_str.strip()

    if not base64_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty Base64 audio data",
        )

    # --------------------------------------------------------
    # Remove data URI prefix if present.
    # --------------------------------------------------------
    if "," in base64_str:
        prefix, encoded_data = base64_str.split(",", 1)

        if not prefix.lower().startswith("data:"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Base64 audio data",
            )

        base64_str = encoded_data

    try:
        # validate=True ensures invalid Base64 characters
        # are rejected.
        audio_bytes = base64.b64decode(
            base64_str,
            validate=True,
        )

    except (binascii.Error, ValueError, TypeError) as exc:
        logger.warning(
            "Invalid Base64 audio: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Base64 audio data",
        )

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decoded audio is empty",
        )

    if len(audio_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Audio file too large. Maximum size: "
                f"{MAX_FILE_SIZE // (1024 * 1024)} MB"
            ),
        )

    return audio_bytes


def validate_base64_format(format_type: str) -> str:
    """
    Validate and normalize a Base64 audio format.
    """

    if not format_type:
        format_type = DEFAULT_BASE64_FORMAT

    format_type = str(format_type).strip().lower()

    # Allow callers to send ".webm" as well as "webm".
    if format_type.startswith("."):
        format_type = format_type[1:]

    extension = f".{format_type}"

    if extension not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported audio format. Supported: "
                f"{', '.join(SUPPORTED_FORMATS)}"
            ),
        )

    return format_type


def create_temp_audio_file(
    content: bytes,
    suffix: str,
) -> str:
    """
    Create a temporary audio file and return its path.
    """

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "File too large. Maximum size: "
                f"{MAX_FILE_SIZE // (1024 * 1024)} MB"
            ),
        )

    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False,
    ) as temp_file:
        temp_file.write(content)
        return temp_file.name


def remove_temp_file(file_path: Optional[str]) -> None:
    """Safely remove a temporary file."""

    if not file_path:
        return

    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except OSError as exc:
        logger.warning(
            "Could not remove temporary file '%s': %s",
            file_path,
            exc,
        )


# ============================================================
# MAIN TRANSCRIPTION ENDPOINT
# ============================================================

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    language: Optional[str] = "en",
):
    """
    Transcribe an uploaded audio file to text.
    """

    filename = audio.filename or ""

    # --------------------------------------------------------
    # Validate format.
    # --------------------------------------------------------
    if not validate_audio_format(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported audio format. Supported: "
                f"{', '.join(SUPPORTED_FORMATS)}"
            ),
        )

    suffix = get_audio_extension(filename)

    tmp_path: Optional[str] = None

    try:
        # ----------------------------------------------------
        # Read uploaded file.
        # ----------------------------------------------------
        content = await audio.read()

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty audio file",
            )

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    "File too large. Maximum size: "
                    f"{MAX_FILE_SIZE // (1024 * 1024)} MB"
                ),
            )

        # ----------------------------------------------------
        # Save temporary file.
        # ----------------------------------------------------
        tmp_path = create_temp_audio_file(
            content,
            suffix,
        )

        # ----------------------------------------------------
        # Duration.
        # ----------------------------------------------------
        duration = get_audio_duration(tmp_path)

        # ----------------------------------------------------
        # Whisper transcription.
        # ----------------------------------------------------
        text = await transcribe_audio_async(tmp_path)

        if text is None:
            text = ""

        text = str(text).strip()

        response = {
            "text": text,
            "success": True,
            "language": language,
            "duration_seconds": round(duration, 2),
            "filename": filename,
            "file_size_bytes": len(content),
            "timestamp": datetime.now().isoformat(),
        }

        # ----------------------------------------------------
        # Background logging.
        # ----------------------------------------------------
        if background_tasks is not None:
            background_tasks.add_task(
                log_transcription,
                text,
                len(content),
                duration,
            )

        return response

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Transcription error for '%s': %s",
            filename,
            exc,
        )

        return {
            "text": "",
            "error": str(exc),
            "success": False,
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
        }

    finally:
        remove_temp_file(tmp_path)

        try:
            await audio.close()
        except Exception:
            pass


# ============================================================
# BATCH TRANSCRIPTION
# ============================================================

@router.post("/transcribe/batch")
async def transcribe_batch(
    audios: List[UploadFile] = File(...),
    max_parallel: int = 3,
):
    """
    Transcribe multiple audio files.

    The endpoint keeps processing sequentially by default for
    predictable memory usage. max_parallel is retained for
    frontend/API compatibility.
    """

    if len(audios) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Maximum {MAX_BATCH_FILES} audio files "
                "per batch"
            ),
        )

    if len(audios) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one audio file is required",
        )

    # Normalize the requested parallelism even though the
    # current implementation intentionally processes one file
    # at a time to avoid excessive memory usage.
    try:
        max_parallel = int(max_parallel)
    except (ValueError, TypeError):
        max_parallel = 1

    max_parallel = max(
        1,
        min(max_parallel, 3),
    )

    results = []

    for audio in audios:
        filename = audio.filename or ""

        if not validate_audio_format(filename):
            results.append(
                {
                    "filename": filename,
                    "error": (
                        "Unsupported format. Supported: "
                        f"{', '.join(SUPPORTED_FORMATS)}"
                    ),
                    "success": False,
                }
            )
            continue

        content = b""

        try:
            content = await audio.read()

            if not content:
                results.append(
                    {
                        "filename": filename,
                        "error": "Empty file",
                        "success": False,
                    }
                )
                continue

            if len(content) > MAX_FILE_SIZE:
                results.append(
                    {
                        "filename": filename,
                        "error": (
                            "File too large. Maximum size: "
                            f"{MAX_FILE_SIZE // (1024 * 1024)} MB"
                        ),
                        "success": False,
                    }
                )
                continue

            suffix = get_audio_extension(filename)

            tmp_path = create_temp_audio_file(
                content,
                suffix,
            )

            try:
                text = await transcribe_audio_async(
                    tmp_path
                )

                results.append(
                    {
                        "filename": filename,
                        "text": str(text or "").strip(),
                        "success": True,
                        "file_size_bytes": len(content),
                    }
                )

            finally:
                remove_temp_file(tmp_path)

        except Exception as exc:
            logger.exception(
                "Batch transcription failed for '%s': %s",
                filename,
                exc,
            )

            results.append(
                {
                    "filename": filename,
                    "error": str(exc),
                    "success": False,
                }
            )

        finally:
            try:
                await audio.close()
            except Exception:
                pass

    return {
        "success": True,
        "total_files": len(audios),
        "transcriptions": results,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# BASE64 TRANSCRIPTION
# ============================================================

@router.post("/transcribe/base64")
async def transcribe_base64(
    data: Dict[str, Any],
    background_tasks: BackgroundTasks = None,
):
    """
    Transcribe Base64-encoded audio.
    """

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be a JSON object",
        )

    if "audio" not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'audio' field in request body",
        )

    audio_bytes = decode_base64_audio(
        data["audio"]
    )

    format_type = validate_base64_format(
        data.get(
            "format",
            DEFAULT_BASE64_FORMAT,
        )
    )

    suffix = f".{format_type}"

    tmp_path: Optional[str] = None

    try:
        tmp_path = create_temp_audio_file(
            audio_bytes,
            suffix,
        )

        text = await transcribe_audio_async(
            tmp_path
        )

        text = str(text or "").strip()

        if background_tasks is not None:
            background_tasks.add_task(
                log_transcription,
                text,
                len(audio_bytes),
                get_audio_duration(tmp_path),
            )

        return {
            "text": text,
            "success": True,
            "file_size_bytes": len(audio_bytes),
            "format": format_type,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Base64 transcription error: %s",
            exc,
        )

        return {
            "text": "",
            "error": str(exc),
            "success": False,
            "format": format_type,
            "timestamp": datetime.now().isoformat(),
        }

    finally:
        remove_temp_file(tmp_path)


# ============================================================
# SUPPORTED FORMATS
# ============================================================

@router.get("/supported-formats")
async def get_supported_formats():
    """Return supported audio formats and size limit."""

    return {
        "formats": SUPPORTED_FORMATS,
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "description": (
            "Whisper AI supports multiple audio formats"
        ),
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get("/health")
async def health_check():
    """Check the health of the voice service."""

    try:
        model_loaded = whisper is not None

        return {
            "status": (
                "healthy"
                if model_loaded
                else "degraded"
            ),
            "model_loaded": model_loaded,
            "supported_formats": SUPPORTED_FORMATS,
            "max_file_size_mb": (
                MAX_FILE_SIZE // (1024 * 1024)
            ),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.exception(
            "Voice health check failed: %s",
            exc,
        )

        return {
            "status": "unhealthy",
            "model_loaded": False,
            "error": str(exc),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================
# TEST ENDPOINT
# ============================================================

@router.get("/test")
async def test_voice():
    """Check whether the voice API is working."""

    return {
        "status": "ok",
        "message": "Voice API is working",
        "model_loaded": whisper is not None,
        "supported_formats": SUPPORTED_FORMATS,
        "timestamp": datetime.now().isoformat(),
    }

async def log_transcription(
    text: str,
    file_size: int,
    duration: float,
):
    """Log a completed transcription."""

    logger.info(
        "Transcription: '%s...' - Size: %s bytes, "
        "Duration: %.2fs",
        text[:50],
        file_size,
        duration,
    )