import os
import time
import hashlib
import tempfile
import asyncio
import logging
import subprocess
from typing import Optional, Dict, Any
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from groq import Groq
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

CACHE_SIZE = 50
CACHE_TTL = 86400          # 24 hours
MAX_RETRIES = 3
RETRY_DELAY = 1            # seconds
TIMEOUT = 60                # seconds

# Groq file upload limit used by this application
MAX_FILE_SIZE = 25 * 1024 * 1024

SUPPORTED_FORMATS = [
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".flac",
    ".webm",
    ".mp4",
]


# ============================================================
# CACHE
# ============================================================

class TimeoutCache:
    """Simple TTL-based cache for transcriptions."""

    def __init__(
        self,
        maxsize: int = CACHE_SIZE,
        ttl: int = CACHE_TTL
    ):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl

    def get(self, key: str) -> Optional[str]:

        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]

        if time.time() - timestamp >= self.ttl:
            del self.cache[key]
            return None

        self.cache.move_to_end(key)

        return value

    def set(
        self,
        key: str,
        value: str
    ):

        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = (
            value,
            time.time()
        )

        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()

    def size(self) -> int:
        return len(self.cache)


# Global transcription cache
transcription_cache = TimeoutCache()


# ============================================================
# THREAD POOL
# ============================================================

executor = ThreadPoolExecutor(
    max_workers=2
)


# ============================================================
# AUDIO UTILITIES
# ============================================================

def get_audio_hash(file_path: str) -> str:
    """
    Generate an MD5 hash from the audio file.
    Used as the transcription cache key.
    """

    hash_md5 = hashlib.md5()

    with open(file_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def get_audio_duration(file_path: str) -> float:
    """
    Get audio duration using ffprobe.

    Falls back to the Python wave module for WAV files.
    """

    try:

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode == 0:

            duration_text = result.stdout.strip()

            if duration_text:
                return float(duration_text)

    except (
        FileNotFoundError,
        subprocess.SubprocessError,
        ValueError,
    ) as e:

        logger.debug(
            "[WHISPER] ffprobe unavailable/failed: %s",
            e
        )

    # WAV fallback
    if file_path.lower().endswith(".wav"):

        try:

            import wave

            with wave.open(
                file_path,
                "rb"
            ) as wav:

                frames = wav.getnframes()
                rate = wav.getframerate()

                if rate > 0:
                    return frames / float(rate)

        except Exception as e:

            logger.debug(
                "[WHISPER] WAV duration detection failed: %s",
                e
            )

    return 0.0


def get_audio_size(file_path: str) -> int:
    """Return audio file size in bytes."""

    return os.path.getsize(file_path)


def convert_to_supported_format(
    input_path: str
) -> str:
    """
    Convert unsupported audio into MP3 using FFmpeg.

    Output:
        16 kHz
        mono
        32 kbps MP3
    """

    output_path = tempfile.NamedTemporaryFile(
        suffix=".mp3",
        delete=False
    ).name

    try:

        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                input_path,
                "-acodec",
                "mp3",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-b:a",
                "32k",
                output_path,
                "-y",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if (
            result.returncode == 0
            and os.path.exists(output_path)
            and os.path.getsize(output_path) > 0
        ):

            logger.debug(
                "[WHISPER] Audio converted successfully"
            )

            return output_path

        logger.warning(
            "[WHISPER] FFmpeg conversion failed: %s",
            result.stderr[-1000:] if result.stderr else "unknown error"
        )

    except FileNotFoundError:

        logger.error(
            "[WHISPER] FFmpeg is not installed."
        )

    except subprocess.TimeoutExpired:

        logger.error(
            "[WHISPER] FFmpeg conversion timed out."
        )

    except Exception as e:

        logger.exception(
            "[WHISPER] Audio conversion error: %s",
            e
        )

    # Remove failed output
    if os.path.exists(output_path):

        try:
            os.unlink(output_path)
        except OSError:
            pass

    return input_path


# ============================================================
# WHISPER CLIENT
# ============================================================

class WhisperClient:

    def __init__(self):

        self.api_key = os.getenv(
            "GROQ_API_KEY"
        )

        if not self.api_key:

            logger.warning(
                "[WHISPER] GROQ_API_KEY is not configured."
            )

            self.client = None

        else:

            try:

                self.client = Groq(
                    api_key=self.api_key,
                    timeout=TIMEOUT
                )

                logger.info(
                    "[WHISPER] Groq client initialized"
                )

            except Exception as e:

                self.client = None

                logger.exception(
                    "[WHISPER] Failed to initialize Groq client: %s",
                    e
                )

        # Keep your existing Whisper model.
        self.model = "whisper-large-v3"

        self.response_format = "json"

        self.language = "en"

        self.temperature = 0.0

        logger.info(
            "[WHISPER] WhisperClient initialized"
        )


    # ========================================================
    # CACHE KEY
    # ========================================================

    def _get_cache_key(
        self,
        file_path: str
    ) -> str:

        return get_audio_hash(
            file_path
        )


    # ========================================================
    # AUDIO PREPROCESSING
    # ========================================================

    def _preprocess_audio(
        self,
        file_path: str
    ) -> str:
        """
        Validate and preprocess an audio file.
        """

        if not os.path.exists(file_path):

            raise FileNotFoundError(
                f"Audio file not found: {file_path}"
            )

        file_size = get_audio_size(
            file_path
        )

        # ----------------------------------------------------
        # File size validation
        # ----------------------------------------------------

        if file_size > MAX_FILE_SIZE:

            logger.warning(
                "[WHISPER] File too large: %d bytes",
                file_size
            )

            raise ValueError(
                "File size exceeds maximum of "
                f"{MAX_FILE_SIZE // (1024 * 1024)} MB"
            )

        if file_size <= 0:

            raise ValueError(
                "Audio file is empty"
            )

        # ----------------------------------------------------
        # Format validation
        # ----------------------------------------------------

        extension = os.path.splitext(
            file_path
        )[1].lower()

        if extension not in SUPPORTED_FORMATS:

            logger.info(
                "[WHISPER] Unsupported format %s. "
                "Attempting FFmpeg conversion.",
                extension
            )

            converted_path = (
                convert_to_supported_format(
                    file_path
                )
            )

            if converted_path == file_path:

                raise ValueError(
                    f"Unsupported audio format: {extension}"
                )

            return converted_path

        return file_path


    # ========================================================
    # TRANSCRIBE
    # ========================================================

    def transcribe(
        self,
        audio_file_path: str,
        use_cache: bool = True,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        """
        Transcribe an audio file using Groq Whisper.

        Args:
            audio_file_path:
                Local audio file path.

            use_cache:
                Whether cached transcription should be used.

            language:
                Language code such as "en" or "hi".

            prompt:
                Optional transcription prompt.

        Returns:
            Transcribed text.
        """

        if self.client is None:

            raise RuntimeError(
                "GROQ_API_KEY is not configured. "
                "Please configure it in the environment."
            )

        if not os.path.exists(
            audio_file_path
        ):

            raise FileNotFoundError(
                f"Audio file not found: {audio_file_path}"
            )

        # ----------------------------------------------------
        # Cache
        # ----------------------------------------------------

        cache_key = self._get_cache_key(
            audio_file_path
        )

        if use_cache:

            cached = transcription_cache.get(
                cache_key
            )

            if cached is not None:

                logger.debug(
                    "[WHISPER] Cache hit: %s",
                    os.path.basename(
                        audio_file_path
                    )
                )

                return cached

        # ----------------------------------------------------
        # Preprocess
        # ----------------------------------------------------

        processed_path = (
            self._preprocess_audio(
                audio_file_path
            )
        )

        try:

            duration = get_audio_duration(
                processed_path
            )

            file_size = get_audio_size(
                processed_path
            )

            logger.info(
                "[WHISPER] Transcribing %s "
                "(%.1fs, %d KB)",
                os.path.basename(
                    audio_file_path
                ),
                duration,
                file_size // 1024,
            )

            # ------------------------------------------------
            # Retry API call
            # ------------------------------------------------

            last_error = None

            for attempt in range(
                MAX_RETRIES
            ):

                try:

                    with open(
                        processed_path,
                        "rb"
                    ) as file:

                        transcription = (
                            self.client
                            .audio
                            .transcriptions
                            .create(
                                file=(
                                    os.path.basename(
                                        processed_path
                                    ),
                                    file.read()
                                ),
                                model=self.model,
                                response_format=(
                                    self.response_format
                                ),
                                language=(
                                    language
                                    or self.language
                                ),
                                temperature=(
                                    self.temperature
                                ),
                                prompt=prompt,
                            )
                        )

                    text = (
                        getattr(
                            transcription,
                            "text",
                            ""
                        )
                        or ""
                    ).strip()

                    if use_cache:

                        transcription_cache.set(
                            cache_key,
                            text
                        )

                    logger.info(
                        "[WHISPER] Transcription complete: "
                        "%d characters",
                        len(text)
                    )

                    return text

                except Exception as e:

                    last_error = e

                    logger.warning(
                        "[WHISPER] Attempt %d/%d failed: %s",
                        attempt + 1,
                        MAX_RETRIES,
                        e
                    )

                    if attempt < MAX_RETRIES - 1:

                        time.sleep(
                            RETRY_DELAY
                            * (attempt + 1)
                        )

            raise RuntimeError(
                "Transcription failed after "
                f"{MAX_RETRIES} attempts: {last_error}"
            )

        finally:

            # Remove converted temporary file.
            if (
                processed_path != audio_file_path
                and os.path.exists(processed_path)
            ):

                try:
                    os.unlink(
                        processed_path
                    )

                except OSError as e:

                    logger.warning(
                        "[WHISPER] Could not remove "
                        "temporary file: %s",
                        e
                    )


    # ========================================================
    # TRANSCRIPTION WITH TIMESTAMPS
    # ========================================================

    def transcribe_with_timestamps(
        self,
        audio_file_path: str
    ) -> Dict[str, Any]:
        """
        Transcribe with word-level timestamps.
        """

        if self.client is None:

            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        processed_path = (
            self._preprocess_audio(
                audio_file_path
            )
        )

        try:

            with open(
                processed_path,
                "rb"
            ) as file:

                transcription = (
                    self.client
                    .audio
                    .transcriptions
                    .create(
                        file=(
                            os.path.basename(
                                processed_path
                            ),
                            file.read()
                        ),
                        model=self.model,
                        response_format="verbose_json",
                        timestamp_granularities=[
                            "word"
                        ],
                    )
                )

            words = []

            transcription_words = getattr(
                transcription,
                "words",
                None
            )

            if transcription_words:

                words = [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                    }
                    for word in transcription_words
                ]

            return {
                "text": (
                    getattr(
                        transcription,
                        "text",
                        ""
                    )
                    or ""
                ),
                "language": getattr(
                    transcription,
                    "language",
                    None
                ),
                "duration": getattr(
                    transcription,
                    "duration",
                    None
                ),
                "words": words,
            }

        finally:

            if (
                processed_path != audio_file_path
                and os.path.exists(processed_path)
            ):

                try:
                    os.unlink(
                        processed_path
                    )
                except OSError:
                    pass


    # ========================================================
    # LONG AUDIO
    # ========================================================

    def transcribe_segments(
        self,
        audio_file_path: str,
        segment_duration: int = 60
    ) -> str:
        """
        Transcribe long audio.

        The current implementation delegates to the regular
        transcription method, preserving existing behavior.
        """

        return self.transcribe(
            audio_file_path
        )


    # ========================================================
    # CACHE
    # ========================================================

    def clear_cache(self):
        """Clear transcription cache."""

        transcription_cache.clear()

        logger.info(
            "[WHISPER] Transcription cache cleared"
        )


    def get_cache_stats(
        self
    ) -> Dict[str, Any]:
        """Return cache statistics."""

        return {
            "size": transcription_cache.size(),
            "max_size": CACHE_SIZE,
            "ttl_seconds": CACHE_TTL,
        }


    # ========================================================
    # MODEL INFO
    # ========================================================

    def get_model_info(
        self
    ) -> Dict[str, Any]:
        """Return Whisper configuration."""

        return {
            "model": self.model,
            "supported_formats": SUPPORTED_FORMATS,
            "max_file_size_mb": (
                MAX_FILE_SIZE
                // (1024 * 1024)
            ),
            "language": self.language,
            "cache_enabled": True,
            "cache_size": transcription_cache.size(),
        }


# ============================================================
# SINGLETON
# ============================================================

whisper = WhisperClient()


# ============================================================
# ASYNC TRANSCRIPTION
# ============================================================

async def transcribe_async(
    audio_file_path: str,
    use_cache: bool = True
) -> str:
    """Async wrapper for transcription."""

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        executor,
        whisper.transcribe,
        audio_file_path,
        use_cache,
    )


# ============================================================
# ASYNC BYTES TRANSCRIPTION
# ============================================================

async def transcribe_bytes_async(
    audio_bytes: bytes,
    filename: str = "audio.webm"
) -> str:
    """Transcribe audio directly from bytes."""

    extension = os.path.splitext(
        filename
    )[1].lower()

    if not extension:
        extension = ".webm"

    tmp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False
        ) as tmp:

            tmp.write(audio_bytes)

            tmp_path = tmp.name

        return await transcribe_async(
            tmp_path
        )

    finally:

        if (
            tmp_path
            and os.path.exists(tmp_path)
        ):

            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ============================================================
# AUDIO FORMAT UTILITY
# ============================================================

def is_supported_audio(
    filename: str
) -> bool:
    """Check whether an audio format is supported."""

    extension = os.path.splitext(
        filename
    )[1].lower()

    return extension in SUPPORTED_FORMATS