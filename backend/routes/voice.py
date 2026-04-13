from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from typing import Optional, List
import tempfile
import os
import asyncio
import base64
import wave
import struct
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
from ai_models.whisper_client import whisper

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for CPU-intensive operations
executor = ThreadPoolExecutor(max_workers=2)

# Supported audio formats
SUPPORTED_FORMATS = ['.webm', '.mp3', '.wav', '.m4a', '.ogg', '.flac']
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

# ==================== HELPER FUNCTIONS ====================

async def transcribe_audio_async(audio_path: str) -> str:
    """Transcribe audio asynchronously"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        whisper.transcribe,
        audio_path
    )

def validate_audio_format(filename: str) -> bool:
    """Check if audio format is supported"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in SUPPORTED_FORMATS

def get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds (for WAV files)"""
    try:
        if file_path.endswith('.wav'):
            with wave.open(file_path, 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                return frames / float(rate)
    except Exception:
        pass
    return 0.0

def decode_base64_audio(base64_str: str) -> bytes:
    """Decode base64 audio to bytes"""
    try:
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        return base64.b64decode(base64_str)
    except Exception as e:
        logger.error(f"Base64 decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 audio data"
        )

# ==================== MAIN TRANSCRIPTION ENDPOINTS ====================

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    language: Optional[str] = "en"
):
    """Transcribe audio file to text"""
    
    # Validate file type
    if not validate_audio_format(audio.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # Read audio content
    content = await audio.read()
    
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file"
        )
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB"
        )
    
    # Save to temp file
    suffix = os.path.splitext(audio.filename)[1].lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Get audio duration
        duration = get_audio_duration(tmp_path)
        
        # Transcribe
        text = await transcribe_audio_async(tmp_path)
        
        # Prepare response
        response = {
            "text": text,
            "success": True,
            "language": language,
            "duration_seconds": round(duration, 2),
            "filename": audio.filename,
            "file_size_bytes": len(content),
            "timestamp": datetime.now().isoformat()
        }
        
        # Log transcription in background
        if background_tasks:
            background_tasks.add_task(
                log_transcription,
                text,
                len(content),
                duration
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {
            "text": "",
            "error": str(e),
            "success": False,
            "timestamp": datetime.now().isoformat()
        }
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@router.post("/transcribe/batch")
async def transcribe_batch(
    audios: List[UploadFile] = File(...),
    max_parallel: int = 3
):
    """Transcribe multiple audio files"""
    
    if len(audios) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 audio files per batch"
        )
    
    results = []
    
    for audio in audios:
        if not validate_audio_format(audio.filename):
            results.append({
                "filename": audio.filename,
                "error": f"Unsupported format",
                "success": False
            })
            continue
        
        content = await audio.read()
        
        if len(content) == 0:
            results.append({
                "filename": audio.filename,
                "error": "Empty file",
                "success": False
            })
            continue
        
        suffix = os.path.splitext(audio.filename)[1].lower()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            text = await transcribe_audio_async(tmp_path)
            results.append({
                "filename": audio.filename,
                "text": text,
                "success": True,
                "file_size_bytes": len(content)
            })
        except Exception as e:
            results.append({
                "filename": audio.filename,
                "error": str(e),
                "success": False
            })
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    return {
        "success": True,
        "total_files": len(audios),
        "transcriptions": results,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/transcribe/base64")
async def transcribe_base64(
    data: dict,
    background_tasks: BackgroundTasks = None
):
    """Transcribe base64 encoded audio"""
    
    if 'audio' not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'audio' field in request body"
        )
    
    try:
        audio_bytes = decode_base64_audio(data['audio'])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 data: {str(e)}"
        )
    
    # Detect format from data or use default
    format_type = data.get('format', 'webm')
    suffix = f".{format_type}"
    
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    
    try:
        text = await transcribe_audio_async(tmp_path)
        
        return {
            "text": text,
            "success": True,
            "file_size_bytes": len(audio_bytes),
            "format": format_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {
            "text": "",
            "error": str(e),
            "success": False
        }
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported audio formats"""
    return {
        "formats": SUPPORTED_FORMATS,
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "description": "Whisper AI supports multiple audio formats"
    }

@router.get("/health")
async def health_check():
    """Health check for voice service"""
    try:
        test_result = whisper is not None
        
        return {
            "status": "healthy" if test_result else "degraded",
            "model_loaded": test_result,
            "supported_formats": SUPPORTED_FORMATS,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/test")
async def test_voice():
    """Test if voice API is working"""
    return {
        "status": "ok",
        "message": "Voice API is working",
        "model_loaded": whisper is not None,
        "supported_formats": SUPPORTED_FORMATS,
        "timestamp": datetime.now().isoformat()
    }

# ==================== LOGGING FUNCTION ====================

async def log_transcription(text: str, file_size: int, duration: float):
    """Background task to log transcription events"""
    logger.info(f"Transcription: '{text[:50]}...' - Size: {file_size} bytes, Duration: {duration}s")