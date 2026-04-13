import os
import time
import hashlib
import tempfile
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from functools import lru_cache
from collections import OrderedDict
import subprocess
from groq import Groq
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

CACHE_SIZE = 50
CACHE_TTL = 86400  # 24 hours
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
TIMEOUT = 60  # seconds
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
SUPPORTED_FORMATS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm', '.mp4']

# ==================== CACHE IMPLEMENTATION ====================

class TimeoutCache:
    """Simple TTL-based cache for transcriptions"""
    def __init__(self, maxsize: int = CACHE_SIZE, ttl: int = CACHE_TTL):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: str):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time())
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)
    
    def clear(self):
        self.cache.clear()
    
    def size(self) -> int:
        return len(self.cache)

# Global cache instance
transcription_cache = TimeoutCache()

# Thread pool for CPU-intensive operations
executor = ThreadPoolExecutor(max_workers=2)

# ==================== AUDIO PROCESSING ====================

def get_audio_hash(file_path: str) -> str:
    """Generate hash of audio file for caching"""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds using ffprobe or wave"""
    try:
        # Try using ffprobe if available
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    
    # Fallback for WAV files
    if file_path.endswith('.wav'):
        try:
            import wave
            with wave.open(file_path, 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                return frames / float(rate)
        except:
            pass
    
    return 0.0

def get_audio_size(file_path: str) -> int:
    """Get audio file size in bytes"""
    return os.path.getsize(file_path)

def convert_to_supported_format(input_path: str) -> str:
    """Convert audio to supported format using ffmpeg"""
    output_path = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
    
    try:
        subprocess.run(
            ['ffmpeg', '-i', input_path, '-acodec', 'mp3', '-ar', '16000',
             '-ac', '1', '-b:a', '32k', output_path, '-y'],
            capture_output=True, timeout=30, check=False
        )
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
    except Exception as e:
        logger.warning(f"Audio conversion failed: {e}")
    
    return input_path

# ==================== WHISPER CLIENT ====================

class WhisperClient:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "whisper-large-v3"
        self.response_format = "json"
        self.language = "en"
        self.temperature = 0.0
        
        logger.info("WhisperClient initialized")
    
    def _get_cache_key(self, file_path: str) -> str:
        """Generate cache key from file content"""
        return get_audio_hash(file_path)
    
    def _preprocess_audio(self, file_path: str) -> str:
        """Preprocess audio for better transcription"""
        file_size = get_audio_size(file_path)
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"File too large: {file_size} bytes")
            raise ValueError(f"File size exceeds maximum of {MAX_FILE_SIZE // (1024*1024)} MB")
        
        # Check format
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_FORMATS:
            logger.warning(f"Unsupported format: {ext}, attempting conversion")
            return convert_to_supported_format(file_path)
        
        return file_path
    
    def transcribe(self, audio_file_path: str, use_cache: bool = True, 
                   language: Optional[str] = None, prompt: Optional[str] = None) -> str:
        """
        Transcribe audio file with caching and retry logic
        
        Args:
            audio_file_path: Path to audio file
            use_cache: Whether to use cache
            language: Language code (e.g., 'en', 'hi')
            prompt: Optional prompt to guide transcription
        
        Returns:
            Transcribed text
        """
        # Check cache first
        cache_key = self._get_cache_key(audio_file_path)
        if use_cache:
            cached = transcription_cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for: {audio_file_path}")
                return cached
        
        # Preprocess audio
        processed_path = self._preprocess_audio(audio_file_path)
        
        # Get audio info
        duration = get_audio_duration(processed_path)
        file_size = get_audio_size(processed_path)
        logger.info(f"Transcribing: {os.path.basename(audio_file_path)} "
                   f"({duration:.1f}s, {file_size//1024}KB)")
        
        # Transcribe with retries
        for attempt in range(MAX_RETRIES):
            try:
                with open(processed_path, "rb") as file:
                    transcription = self.client.audio.transcriptions.create(
                        file=(os.path.basename(processed_path), file.read()),
                        model=self.model,
                        response_format=self.response_format,
                        language=language or self.language,
                        temperature=self.temperature,
                        prompt=prompt
                    )
                
                text = transcription.text.strip()
                
                # Cache result
                if use_cache:
                    transcription_cache.set(cache_key, text)
                
                # Clean up converted file if different from original
                if processed_path != audio_file_path and os.path.exists(processed_path):
                    os.unlink(processed_path)
                
                logger.info(f"Transcription complete: {len(text)} chars")
                return text
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    if processed_path != audio_file_path and os.path.exists(processed_path):
                        os.unlink(processed_path)
                    raise Exception(f"Transcription failed after {MAX_RETRIES} attempts: {e}")
        
        return ""
    
    def transcribe_with_timestamps(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe with word-level timestamps"""
        processed_path = self._preprocess_audio(audio_file_path)
        
        try:
            with open(processed_path, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(processed_path), file.read()),
                    model=self.model,
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
            
            result = {
                "text": transcription.text,
                "language": transcription.language,
                "duration": transcription.duration,
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end}
                    for w in transcription.words
                ] if hasattr(transcription, 'words') else []
            }
            
            if processed_path != audio_file_path and os.path.exists(processed_path):
                os.unlink(processed_path)
            
            return result
            
        except Exception as e:
            if processed_path != audio_file_path and os.path.exists(processed_path):
                os.unlink(processed_path)
            raise e
    
    def transcribe_segments(self, audio_file_path: str, segment_duration: int = 60) -> str:
        """Transcribe long audio by splitting into segments"""
        # This is useful for very long files
        # For now, just use regular transcription
        return self.transcribe(audio_file_path)
    
    def clear_cache(self):
        """Clear the transcription cache"""
        transcription_cache.clear()
        logger.info("Transcription cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": transcription_cache.size(),
            "max_size": CACHE_SIZE,
            "ttl_seconds": CACHE_TTL
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model": self.model,
            "supported_formats": SUPPORTED_FORMATS,
            "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "language": self.language,
            "cache_enabled": True,
            "cache_size": transcription_cache.size()
        }

# Create singleton instance
whisper = WhisperClient()

# ==================== ASYNC WRAPPER ====================

async def transcribe_async(audio_file_path: str, use_cache: bool = True) -> str:
    """Async wrapper for transcription"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        whisper.transcribe,
        audio_file_path,
        use_cache
    )

async def transcribe_bytes_async(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe audio from bytes"""
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    
    try:
        return await transcribe_async(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

# ==================== UTILITY FUNCTIONS ====================

def is_supported_audio(filename: str) -> bool:
    """Check if audio format is supported"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in SUPPORTED_FORMATS