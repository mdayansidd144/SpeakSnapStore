# endpoint awaaz ke liye
from fastapi import APIRouter, UploadFile, File
import tempfile
import os
from ai_models.whisper_client import whisper
router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """convert spoken audio to text"""
    # save uploaded audio temporarily
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:  # ← Fixed: delete=False
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        text = whisper.transcribe(tmp_path)
        return {"text": text, "success": True}
    except Exception as e:
        return {"text": "", "error": str(e), "success": False}
    finally:
        os.unlink(tmp_path)