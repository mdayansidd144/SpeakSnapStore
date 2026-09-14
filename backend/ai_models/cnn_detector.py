import cv2
import numpy as np
import tempfile
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ============================================================
# YOLO IMPORT
# ============================================================

try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
    logger.info("[CNN] Ultralytics YOLO is available")

except ImportError:
    YOLO_AVAILABLE = False
    logger.error(
        "[CNN] Ultralytics is not installed. "
        "Install it with: pip install ultralytics"
    )


# ============================================================
# THREAD POOL
# ============================================================

executor = ThreadPoolExecutor(max_workers=4)


# ============================================================
# CNN / YOLO DETECTOR
# ============================================================

class CNNDetector:

    def __init__(self, model_type: str = "auto"):
        """
        Initialize the object detector.

        model_type:
            "auto"      -> use YOLO
            "yolo"      -> use YOLO
        """

        self.model_type = model_type
        self.model = None
        self.class_names = []

        # ----------------------------------------------------
        # Inventory-friendly object names
        # ----------------------------------------------------

        self.name_map = {

            # Fruits
            "apple": "apple",
            "banana": "banana",
            "orange": "orange",
            "strawberry": "strawberry",
            "grape": "grape",
            "watermelon": "watermelon",
            "pear": "pear",
            "peach": "peach",
            "mango": "mango",

            # Vegetables
            "carrot": "carrot",
            "broccoli": "broccoli",
            "tomato": "tomato",
            "cucumber": "cucumber",
            "lettuce": "lettuce",
            "potato": "potato",
            "onion": "onion",
            "garlic": "garlic",
            "pepper": "pepper",

            # Electronics
            "laptop": "laptop",
            "cell phone": "phone",
            "cellphone": "phone",
            "smartphone": "phone",
            "keyboard": "keyboard",
            "mouse": "mouse",
            "monitor": "monitor",
            "television": "tv",
            "tv": "tv",
            "remote": "remote",

            # Stationery
            "book": "book",
            "notebook": "notebook",
            "pen": "pen",
            "pencil": "pencil",
            "eraser": "eraser",
            "ruler": "ruler",
            "scissors": "scissors",

            # Household
            "bottle": "bottle",
            "cup": "cup",
            "chair": "chair",
            "table": "table",
            "plate": "plate",
            "bowl": "bowl",
            "spoon": "spoon",
            "fork": "fork",
            "knife": "knife",
            "towel": "towel",

            # Food
            "pizza": "pizza",
            "burger": "burger",
            "sandwich": "sandwich",
            "cake": "cake",
            "donut": "donut",
            "cookie": "cookie",
            "ice cream": "ice cream",
            "coffee": "coffee",
            "tea": "tea",

            # Animals
            "dog": "dog",
            "cat": "cat",
            "bird": "bird",
            "fish": "fish",

            # Vehicles
            "car": "car",
            "bicycle": "bicycle",
            "motorcycle": "motorcycle",
            "bus": "bus",
            "truck": "truck",
            "train": "train",
        }

        # ----------------------------------------------------
        # Load YOLO
        # ----------------------------------------------------

        if YOLO_AVAILABLE and model_type in ("auto", "yolo"):
            self._load_yolo()
        else:
            raise RuntimeError(
                "YOLO is required for this application, "
                "but Ultralytics is not available."
            )

        logger.info(
            "[CNN] Detector ready using: %s",
            self.model_type.upper()
        )


    # ========================================================
    # LOAD LOCAL YOLO MODEL
    # ========================================================

    def _load_yolo(self):
        """
        Load the YOLO model bundled with the project.

        Expected structure:

        backend/
            ai_models/
                cnn_detector.py
            yolov8n.pt
        """

        try:

            # cnn_detector.py:
            # backend/ai_models/cnn_detector.py
            #
            # parent      = ai_models
            # parent.parent = backend

            backend_dir = Path(__file__).resolve().parent.parent

            model_path = backend_dir / "yolov8n.pt"

            logger.info(
                "[CNN] Looking for YOLO model at: %s",
                model_path
            )

            if not model_path.exists():
                raise FileNotFoundError(
                    f"YOLO model file was not found: {model_path}"
                )

            # Load local model.
            self.model = YOLO(str(model_path))

            self.model_type = "yolo"

            # Ultralytics normally exposes names as a dict.
            self.class_names = self.model.names

            logger.info(
                "[CNN] YOLO model loaded successfully: %s",
                model_path.name
            )

        except Exception as e:

            self.model = None

            logger.exception(
                "[CNN] Failed to load YOLO model: %s",
                e
            )

            raise RuntimeError(
                f"Unable to load YOLO model: {e}"
            ) from e


    # ========================================================
    # SINGLE OBJECT DETECTION
    # ========================================================

    def detect(
        self,
        image_path: str,
        min_confidence: float = 0.25
    ) -> Tuple[str, float]:
        """
        Detect the highest-confidence object in an image.

        Returns:
            (item_name, confidence)
        """

        try:

            # -----------------------------------------------
            # Validate image
            # -----------------------------------------------

            img = cv2.imread(image_path)

            if img is None:
                logger.error(
                    "[CNN] Could not read image: %s",
                    image_path
                )

                return ("unknown", 0.0)

            start_time = time.time()

            # -----------------------------------------------
            # YOLO detection
            # -----------------------------------------------

            results = self.model(
                image_path,
                conf=min_confidence,
                verbose=False
            )

            if not results:
                return ("unknown", 0.0)

            detections = results[0].boxes

            if detections is None or len(detections) == 0:
                return ("unknown", 0.0)

            # -----------------------------------------------
            # Find highest-confidence detection
            # -----------------------------------------------

            top_box = max(
                detections,
                key=lambda box: float(box.conf[0])
            )

            class_id = int(top_box.cls[0])
            confidence = float(top_box.conf[0])

            class_name = self._get_class_name(class_id)

            friendly_name = self._map_object_name(class_name)

            elapsed = (time.time() - start_time) * 1000

            logger.debug(
                "[CNN] YOLO detection: %s "
                "(%.2f) - %.0fms",
                friendly_name,
                confidence,
                elapsed
            )

            return (
                friendly_name,
                confidence
            )

        except Exception as e:

            logger.exception(
                "[CNN] Detection error: %s",
                e
            )

            return ("error", 0.0)


    # ========================================================
    # MULTIPLE OBJECT DETECTION
    # ========================================================

    def detect_multiple(
        self,
        image_path: str,
        min_confidence: float = 0.25
    ) -> List[Dict[str, Any]]:
        """
        Detect multiple objects in an image.

        Returns:
            [
                {
                    "item": "...",
                    "confidence": 0.95,
                    "bbox": [x1, y1, x2, y2]
                }
            ]
        """

        try:

            results = self.model(
                image_path,
                conf=min_confidence,
                verbose=False
            )

            if not results:
                return []

            detections = results[0].boxes

            if detections is None or len(detections) == 0:
                return []

            objects = []

            for box in detections:

                class_id = int(box.cls[0])

                confidence = float(box.conf[0])

                class_name = self._get_class_name(class_id)

                bbox = box.xyxy[0].tolist()

                friendly_name = self._map_object_name(
                    class_name
                )

                objects.append({
                    "item": friendly_name,
                    "confidence": confidence,
                    "bbox": bbox
                })

            # Highest confidence first.
            objects.sort(
                key=lambda x: x["confidence"],
                reverse=True
            )

            return objects

        except Exception as e:

            logger.exception(
                "[CNN] Multi-detection error: %s",
                e
            )

            return []


    # ========================================================
    # IMAGE BYTES -> SINGLE DETECTION
    # ========================================================

    def detect_from_bytes(
        self,
        image_bytes: bytes,
        min_confidence: float = 0.25
    ) -> Tuple[str, float]:
        """
        Detect object from raw image bytes.
        """

        tmp_path = None

        try:

            with tempfile.NamedTemporaryFile(
                suffix=".jpg",
                delete=False
            ) as tmp:

                tmp.write(image_bytes)

                tmp_path = tmp.name

            return self.detect(
                tmp_path,
                min_confidence
            )

        finally:

            if tmp_path and os.path.exists(tmp_path):

                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


    # ========================================================
    # IMAGE BYTES -> MULTIPLE DETECTION
    # ========================================================

    def detect_multiple_from_bytes(
        self,
        image_bytes: bytes,
        min_confidence: float = 0.25
    ) -> List[Dict[str, Any]]:
        """
        Detect multiple objects from raw image bytes.
        """

        tmp_path = None

        try:

            with tempfile.NamedTemporaryFile(
                suffix=".jpg",
                delete=False
            ) as tmp:

                tmp.write(image_bytes)

                tmp_path = tmp.name

            return self.detect_multiple(
                tmp_path,
                min_confidence
            )

        finally:

            if tmp_path and os.path.exists(tmp_path):

                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


    # ========================================================
    # BATCH DETECTION
    # ========================================================

    def detect_batch(
        self,
        image_paths: List[str],
        min_confidence: float = 0.25
    ) -> List[Tuple[str, float]]:
        """
        Detect objects in multiple images.
        """

        def process_single(path):
            return self.detect(
                path,
                min_confidence
            )

        with ThreadPoolExecutor(
            max_workers=4
        ) as pool:

            return list(
                pool.map(
                    process_single,
                    image_paths
                )
            )


    # ========================================================
    # CLASS NAME HELPER
    # ========================================================

    def _get_class_name(self, class_id: int) -> str:
        """
        Safely get YOLO class name.
        """

        try:

            if isinstance(self.class_names, dict):
                return str(
                    self.class_names.get(
                        class_id,
                        "unknown"
                    )
                )

            if (
                isinstance(self.class_names, list)
                and 0 <= class_id < len(self.class_names)
            ):
                return str(
                    self.class_names[class_id]
                )

        except Exception as e:

            logger.warning(
                "[CNN] Could not resolve class %s: %s",
                class_id,
                e
            )

        return "unknown"


    # ========================================================
    # OBJECT NAME MAPPING
    # ========================================================

    def _map_object_name(self, name: str) -> str:
        """
        Map YOLO class name to an inventory-friendly name.
        """

        if not name:
            return "item"

        name_lower = name.lower().strip()

        # -----------------------------------------------
        # Direct mapping
        # -----------------------------------------------

        for key, value in self.name_map.items():

            if (
                key in name_lower
                or name_lower in key
            ):
                return value

        # -----------------------------------------------
        # Special cases
        # -----------------------------------------------

        if "bottle" in name_lower:
            return "bottle"

        if (
            "phone" in name_lower
            or "cell" in name_lower
        ):
            return "phone"

        if (
            "computer" in name_lower
            or "laptop" in name_lower
        ):
            return "laptop"

        if "book" in name_lower:
            return "book"

        if "chair" in name_lower:
            return "chair"

        if "table" in name_lower:
            return "table"

        if (
            "cup" in name_lower
            or "mug" in name_lower
        ):
            return "cup"

        if (
            "plate" in name_lower
            or "dish" in name_lower
        ):
            return "plate"

        # -----------------------------------------------
        # Clean fallback
        # -----------------------------------------------

        return (
            name_lower.split()[0]
            if name_lower
            else "item"
        )


    # ========================================================
    # MODEL INFORMATION
    # ========================================================

    def get_model_info(self) -> Dict[str, Any]:
        """
        Return information about the loaded model.
        """

        if isinstance(self.class_names, dict):
            class_count = len(self.class_names)

        elif isinstance(self.class_names, list):
            class_count = len(self.class_names)

        else:
            class_count = 0

        return {
            "model_type": self.model_type,
            "model_loaded": self.model is not None,
            "yolo_available": YOLO_AVAILABLE,
            "class_count": class_count,
            "name_mappings": len(self.name_map)
        }


# ============================================================
# SINGLETON
# ============================================================

detector = CNNDetector()


# ============================================================
# ASYNC SINGLE DETECTION
# ============================================================

async def detect_async(
    image_bytes: bytes
) -> Tuple[str, float]:
    """
    Async wrapper for single image detection.
    """

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        executor,
        detector.detect_from_bytes,
        image_bytes
    )


# ============================================================
# ASYNC MULTIPLE DETECTION
# ============================================================

async def detect_multiple_async(
    image_bytes: bytes
) -> List[Dict[str, Any]]:
    """
    Async wrapper for multiple object detection.
    """

    loop = asyncio.get_running_loop()

    return await loop.run_in_executor(
        executor,
        detector.detect_multiple_from_bytes,
        image_bytes
    )