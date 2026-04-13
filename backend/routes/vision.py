from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, status, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
import cv2
import numpy as np
import tempfile
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import base64
from datetime import datetime
import logging
from ai_models.cnn_detector import detector

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for CPU-intensive operations
executor = ThreadPoolExecutor(max_workers=2)

# ==================== HELPER FUNCTIONS ====================

async def process_image_async(image_bytes: bytes) -> tuple:
    """Process image asynchronously"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor, 
        detector.detect_from_bytes, 
        image_bytes
    )

def decode_base64_image(base64_str: str) -> bytes:
    """Decode base64 image to bytes"""
    try:
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        return base64.b64decode(base64_str)
    except Exception as e:
        logger.error(f"Base64 decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 image data"
        )

def get_image_size(image_bytes: bytes) -> tuple:
    """Get image dimensions without saving to disk"""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            return img.shape[1], img.shape[0]  # width, height
        return (0, 0)
    except Exception as e:
        logger.error(f"Error getting image size: {e}")
        return (0, 0)

# ==================== MAIN DETECTION ENDPOINTS ====================

@router.post("/detect")
async def detect_object(
    image: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Detect object from camera image or uploaded file"""
    
    # Validate file type
    if not image.content_type or not image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload an image."
        )
    
    # Read image
    content = await image.read()
    
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file"
        )
    
    # Get image info
    width, height = get_image_size(content)
    
    try:
        # Process detection asynchronously
        item, confidence = await process_image_async(content)
        
        # Prepare response
        response = {
            "detected_item": item if item != "error" else "unknown",
            "confidence": round(float(confidence), 4),
            "success": item != "error",
            "image_info": {
                "width": width,
                "height": height,
                "size_bytes": len(content)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to background tasks for logging (optional)
        if background_tasks:
            background_tasks.add_task(
                log_detection,
                item,
                confidence,
                len(content)
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)}"
        )

@router.post("/detect/batch")
async def detect_batch(
    images: List[UploadFile] = File(...),
    max_parallel: int = 3
):
    """Detect objects in multiple images"""
    
    if len(images) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 images per batch"
        )
    
    results = []
    
    for img in images:
        if not img.content_type or not img.content_type.startswith('image/'):
            results.append({
                "filename": img.filename,
                "error": "Invalid file type",
                "success": False
            })
            continue
        
        content = await img.read()
        
        if len(content) == 0:
            results.append({
                "filename": img.filename,
                "error": "Empty file",
                "success": False
            })
            continue
        
        try:
            item, confidence = await process_image_async(content)
            results.append({
                "filename": img.filename,
                "detected_item": item if item != "error" else "unknown",
                "confidence": round(float(confidence), 4),
                "success": item != "error"
            })
        except Exception as e:
            results.append({
                "filename": img.filename,
                "error": str(e),
                "success": False
            })
    
    return {
        "success": True,
        "total_images": len(images),
        "detections": results,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/detect/base64")
async def detect_base64(
    data: dict,
    background_tasks: BackgroundTasks = None
):
    """Detect object from base64 encoded image"""
    
    if 'image' not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'image' field in request body"
        )
    
    try:
        image_bytes = decode_base64_image(data['image'])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 data: {str(e)}"
        )
    
    width, height = get_image_size(image_bytes)
    
    try:
        item, confidence = await process_image_async(image_bytes)
        
        return {
            "detected_item": item if item != "error" else "unknown",
            "confidence": round(float(confidence), 4),
            "success": item != "error",
            "image_info": {
                "width": width,
                "height": height,
                "size_bytes": len(image_bytes)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)}"
        )

@router.get("/info")
async def get_model_info():
    """Get information about the detection model"""
    return {
        "model_name": "MobileNetV2",
        "model_type": "CNN",
        "input_size": "224x224",
        "classes": 1000,
        "framework": "TensorFlow/Keras",
        "status": "active"
    }

@router.get("/supported-objects")
async def get_supported_objects():
    """Get list of common objects the model can detect"""
    common_objects = [
        "apple", "banana", "orange", "strawberry", "grape",
        "bottle", "cup", "book", "laptop", "phone",
        "keyboard", "mouse", "chair", "table", "monitor",
        "car", "bicycle", "dog", "cat", "bird",
        "pizza", "burger", "sandwich", "cake", "donut"
    ]
    
    return {
        "total_objects": len(common_objects),
        "common_objects": common_objects[:20],
        "note": "Model can detect up to 1000 different objects"
    }

@router.get("/health")
async def health_check():
    """Health check for vision service"""
    try:
        test_result = detector is not None
        
        return {
            "status": "healthy" if test_result else "degraded",
            "model_loaded": test_result,
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
async def test_detection():
    """Test if vision API is working"""
    return {
        "status": "ok",
        "message": "Vision API is working",
        "model_loaded": detector is not None,
        "timestamp": datetime.now().isoformat()
    }

# ==================== LOGGING FUNCTION ====================

async def log_detection(item: str, confidence: float, image_size: int):
    """Background task to log detection events"""
    logger.info(f"Detection: {item} (confidence: {confidence:.2f}) - Size: {image_size} bytes")