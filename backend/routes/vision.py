from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    status,
)
from typing import List, Optional, Dict, Any
import cv2
import numpy as np
import tempfile
import os
import asyncio
import base64
import binascii
from datetime import datetime
import logging

from ai_models.cnn_detector import detector


logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# CONFIGURATION
# ============================================================

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_BATCH_IMAGES = 10

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/gif",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def process_image_async(
    image_bytes: bytes,
) -> tuple:
    """
    Run the synchronous detector in a worker thread so that
    CPU-intensive image processing does not block FastAPI.
    """

    if detector is None:
        raise RuntimeError(
            "Vision detector is not available"
        )

    return await asyncio.to_thread(
        detector.detect_from_bytes,
        image_bytes,
    )


def validate_image_content_type(
    content_type: Optional[str],
) -> bool:
    """Validate the uploaded image MIME type."""

    if not content_type:
        return False

    return content_type.lower() in SUPPORTED_IMAGE_TYPES


def validate_image_bytes(
    image_bytes: bytes,
) -> bool:
    """
    Verify that the supplied bytes can actually be decoded
    as an image by OpenCV.
    """

    if not image_bytes:
        return False

    try:
        nparr = np.frombuffer(
            image_bytes,
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            nparr,
            cv2.IMREAD_COLOR,
        )

        return image is not None

    except Exception as exc:
        logger.debug(
            "Image validation failed: %s",
            exc,
        )
        return False


def get_image_size(
    image_bytes: bytes,
) -> tuple:
    """
    Get image dimensions without saving the image to disk.
    Returns (width, height).
    """

    if not image_bytes:
        return 0, 0

    try:
        nparr = np.frombuffer(
            image_bytes,
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            nparr,
            cv2.IMREAD_COLOR,
        )

        if image is None:
            return 0, 0

        height, width = image.shape[:2]

        return int(width), int(height)

    except Exception as exc:
        logger.debug(
            "Could not determine image dimensions: %s",
            exc,
        )
        return 0, 0


def decode_base64_image(
    base64_str: str,
) -> bytes:
    """
    Decode Base64 image data.

    Supports both raw Base64 and data URLs such as:

        data:image/jpeg;base64,...
    """

    if not isinstance(base64_str, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image data must be a Base64 string",
        )

    base64_str = base64_str.strip()

    if not base64_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty Base64 image data",
        )

    # --------------------------------------------------------
    # Remove data URI prefix.
    # --------------------------------------------------------
    if "," in base64_str:
        prefix, encoded_data = base64_str.split(
            ",",
            1,
        )

        if not prefix.lower().startswith("data:"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Base64 image data",
            )

        base64_str = encoded_data

    try:
        image_bytes = base64.b64decode(
            base64_str,
            validate=True,
        )

    except (
        binascii.Error,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning(
            "Invalid Base64 image: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Base64 image data",
        )

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decoded image is empty",
        )

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Image too large. Maximum size: "
                f"{MAX_IMAGE_SIZE // (1024 * 1024)} MB"
            ),
        )

    return image_bytes


def normalize_detection_result(
    item: Any,
    confidence: Any,
) -> tuple:
    """
    Normalize the detector output into a safe
    (item, confidence) tuple.
    """

    normalized_item = str(
        item if item is not None else "unknown"
    ).strip()

    if not normalized_item:
        normalized_item = "unknown"

    if normalized_item.lower() == "error":
        normalized_item = "unknown"

    try:
        normalized_confidence = float(
            confidence
        )
    except (
        ValueError,
        TypeError,
    ):
        normalized_confidence = 0.0

    # Keep confidence in the expected 0-1 range.
    normalized_confidence = max(
        0.0,
        min(1.0, normalized_confidence),
    )

    return (
        normalized_item,
        normalized_confidence,
    )


def build_detection_response(
    item: Any,
    confidence: Any,
    image_bytes: bytes,
    include_dimensions: bool = True,
) -> Dict[str, Any]:
    """Build a consistent detection response."""

    normalized_item, normalized_confidence = (
        normalize_detection_result(
            item,
            confidence,
        )
    )

    response: Dict[str, Any] = {
        "detected_item": normalized_item,
        "confidence": round(
            normalized_confidence,
            4,
        ),
        "success": normalized_item != "unknown",
        "image_info": {
            "size_bytes": len(image_bytes),
        },
        "timestamp": datetime.now().isoformat(),
    }

    if include_dimensions:
        width, height = get_image_size(
            image_bytes
        )

        response["image_info"].update(
            {
                "width": width,
                "height": height,
            }
        )

    return response


# ============================================================
# MAIN DETECTION ENDPOINT
# ============================================================

@router.post("/detect")
async def detect_object(
    image: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Detect an object from a camera image or uploaded file.
    """

    filename = image.filename or "unknown"

    # --------------------------------------------------------
    # Validate MIME type.
    # --------------------------------------------------------
    if not validate_image_content_type(
        image.content_type
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid file type. Please upload a "
                "JPEG, PNG, WebP, BMP, or GIF image."
            ),
        )

    try:
        # ----------------------------------------------------
        # Read image.
        # ----------------------------------------------------
        content = await image.read()

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file",
            )

        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    "Image too large. Maximum size: "
                    f"{MAX_IMAGE_SIZE // (1024 * 1024)} MB"
                ),
            )

        # ----------------------------------------------------
        # Validate actual image bytes.
        # ----------------------------------------------------
        if not validate_image_bytes(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid image",
            )

        width, height = get_image_size(
            content
        )

        if width <= 0 or height <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine image dimensions",
            )

        # ----------------------------------------------------
        # Run detector.
        # ----------------------------------------------------
        item, confidence = (
            await process_image_async(content)
        )

        response = build_detection_response(
            item,
            confidence,
            content,
        )

        response["filename"] = filename

        # ----------------------------------------------------
        # Background logging.
        # ----------------------------------------------------
        if background_tasks is not None:
            background_tasks.add_task(
                log_detection,
                response["detected_item"],
                response["confidence"],
                len(content),
            )

        return response

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Detection error for '%s': %s",
            filename,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detection failed",
        )

    finally:
        try:
            await image.close()
        except Exception:
            pass


# ============================================================
# BATCH DETECTION
# ============================================================

@router.post("/detect/batch")
async def detect_batch(
    images: List[UploadFile] = File(...),
    max_parallel: int = 3,
):
    """
    Detect objects in multiple images.

    Files are processed sequentially to keep memory usage
    predictable on a small Render instance.
    """

    if len(images) > MAX_BATCH_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Maximum {MAX_BATCH_IMAGES} "
                "images per batch"
            ),
        )

    if not images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image is required",
        )

    # Retain API compatibility with the frontend.
    try:
        max_parallel = int(max_parallel)
    except (
        ValueError,
        TypeError,
    ):
        max_parallel = 1

    max_parallel = max(
        1,
        min(max_parallel, 3),
    )

    results = []

    for image in images:
        filename = image.filename or "unknown"

        try:
            # ------------------------------------------------
            # MIME type.
            # ------------------------------------------------
            if not validate_image_content_type(
                image.content_type
            ):
                results.append(
                    {
                        "filename": filename,
                        "error": "Invalid image file type",
                        "success": False,
                    }
                )
                continue

            content = await image.read()

            if not content:
                results.append(
                    {
                        "filename": filename,
                        "error": "Empty file",
                        "success": False,
                    }
                )
                continue

            if len(content) > MAX_IMAGE_SIZE:
                results.append(
                    {
                        "filename": filename,
                        "error": (
                            "Image too large. Maximum size: "
                            f"{MAX_IMAGE_SIZE // (1024 * 1024)} MB"
                        ),
                        "success": False,
                    }
                )
                continue

            if not validate_image_bytes(content):
                results.append(
                    {
                        "filename": filename,
                        "error": "Invalid image data",
                        "success": False,
                    }
                )
                continue

            # ------------------------------------------------
            # Detection.
            # ------------------------------------------------
            item, confidence = (
                await process_image_async(
                    content
                )
            )

            normalized_item, normalized_confidence = (
                normalize_detection_result(
                    item,
                    confidence,
                )
            )

            results.append(
                {
                    "filename": filename,
                    "detected_item": normalized_item,
                    "confidence": round(
                        normalized_confidence,
                        4,
                    ),
                    "success": (
                        normalized_item != "unknown"
                    ),
                }
            )

        except Exception as exc:
            logger.exception(
                "Batch detection failed for '%s': %s",
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
                await image.close()
            except Exception:
                pass

    return {
        "success": True,
        "total_images": len(images),
        "detections": results,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# BASE64 DETECTION
# ============================================================

@router.post("/detect/base64")
async def detect_base64(
    data: Dict[str, Any],
    background_tasks: BackgroundTasks = None,
):
    """
    Detect an object from Base64-encoded image data.
    """

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be a JSON object",
        )

    if "image" not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'image' field in request body",
        )

    image_bytes = decode_base64_image(
        data["image"]
    )

    if not validate_image_bytes(
        image_bytes
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decoded data is not a valid image",
        )

    try:
        item, confidence = (
            await process_image_async(
                image_bytes
            )
        )

        response = build_detection_response(
            item,
            confidence,
            image_bytes,
        )

        if background_tasks is not None:
            background_tasks.add_task(
                log_detection,
                response["detected_item"],
                response["confidence"],
                len(image_bytes),
            )

        return response

    except Exception as exc:
        logger.exception(
            "Base64 detection error: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detection failed",
        )


# ============================================================
# MODEL INFORMATION
# ============================================================

@router.get("/info")
async def get_model_info():
    """
    Return information about the currently deployed
    object-detection model.
    """

    return {
        "model_name": "YOLOv8n",
        "model_type": "YOLO object detection",
        "input_size": "Dynamic",
        "framework": "Ultralytics",
        "weights": "yolov8n.pt",
        "status": (
            "active"
            if detector is not None
            else "unavailable"
        ),
    }


# ============================================================
# SUPPORTED OBJECTS
# ============================================================

@router.get("/supported-objects")
async def get_supported_objects():
    """
    Return common objects that the bundled YOLO model can
    recognize.
    """

    common_objects = [
        "person",
        "bicycle",
        "car",
        "motorcycle",
        "airplane",
        "bus",
        "train",
        "truck",
        "boat",
        "traffic light",
        "fire hydrant",
        "stop sign",
        "parking meter",
        "bench",
        "bird",
        "cat",
        "dog",
        "horse",
        "sheep",
        "cow",
        "elephant",
        "bear",
        "zebra",
        "giraffe",
        "backpack",
        "umbrella",
        "handbag",
        "tie",
        "suitcase",
        "bottle",
        "wine glass",
        "cup",
        "fork",
        "knife",
        "spoon",
        "bowl",
        "banana",
        "apple",
        "sandwich",
        "orange",
        "broccoli",
        "carrot",
        "pizza",
        "donut",
        "cake",
        "chair",
        "couch",
        "potted plant",
        "bed",
        "dining table",
        "toilet",
        "tv",
        "laptop",
        "mouse",
        "remote",
        "keyboard",
        "cell phone",
        "microwave",
        "oven",
        "toaster",
        "sink",
        "refrigerator",
        "book",
        "clock",
        "vase",
        "scissors",
        "teddy bear",
        "hair drier",
        "toothbrush",
    ]

    return {
        "total_objects": len(common_objects),
        "common_objects": common_objects,
        "note": (
            "The bundled YOLOv8 model is trained on "
            "the COCO object-detection classes."
        ),
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get("/health")
async def health_check():
    """Check the health of the vision service."""

    try:
        model_loaded = detector is not None

        return {
            "status": (
                "healthy"
                if model_loaded
                else "degraded"
            ),
            "model_loaded": model_loaded,
            "model": "YOLOv8n",
            "max_image_size_mb": (
                MAX_IMAGE_SIZE // (1024 * 1024)
            ),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.exception(
            "Vision health check failed: %s",
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
async def test_detection():
    """Check whether the vision API is working."""

    return {
        "status": "ok",
        "message": "Vision API is working",
        "model_loaded": detector is not None,
        "model": "YOLOv8n",
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# LOGGING
# ============================================================

async def log_detection(
    item: str,
    confidence: float,
    image_size: int,
):
    """Log a completed object detection."""

    logger.info(
        "Detection: %s "
        "(confidence: %.2f) - Size: %s bytes",
        item,
        confidence,
        image_size,
    )