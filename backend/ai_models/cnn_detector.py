import cv2
import numpy as np
import tempfile
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import YOLOv8 (preferred), fallback to MobileNetV2
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    print("[CNN] YOLOv8 available - using for better accuracy")
except ImportError:
    YOLO_AVAILABLE = False
    print("[CNN] YOLOv8 not available - falling back to MobileNetV2")
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=4)

class CNNDetector:
    def __init__(self, model_type: str = "auto"):
        """
        Initialize detector with best available model
        model_type: "auto", "yolo", "mobilenet"
        """
        self.model_type = model_type
        self.model = None
        self.class_names = []
        
        # Try to load YOLO first if available
        if YOLO_AVAILABLE and model_type in ["auto", "yolo"]:
            self._load_yolo()
        else:
            self._load_mobilenet()
        
        # Common object name mapping for better inventory names
        self.name_map = {
            # Fruits
            'apple': 'apple', 'banana': 'banana', 'orange': 'orange',
            'strawberry': 'strawberry', 'grape': 'grape', 'watermelon': 'watermelon',
            'pear': 'pear', 'peach': 'peach', 'mango': 'mango',
            # Vegetables
            'carrot': 'carrot', 'broccoli': 'broccoli', 'tomato': 'tomato',
            'cucumber': 'cucumber', 'lettuce': 'lettuce', 'potato': 'potato',
            'onion': 'onion', 'garlic': 'garlic', 'pepper': 'pepper',
            # Electronics
            'laptop': 'laptop', 'cell phone': 'phone', 'smartphone': 'phone',
            'keyboard': 'keyboard', 'mouse': 'mouse', 'monitor': 'monitor',
            'television': 'tv', 'remote': 'remote',
            # Stationery
            'book': 'book', 'notebook': 'notebook', 'pen': 'pen', 'pencil': 'pencil',
            'eraser': 'eraser', 'ruler': 'ruler', 'scissors': 'scissors',
            # Household
            'bottle': 'bottle', 'cup': 'cup', 'chair': 'chair', 'table': 'table',
            'plate': 'plate', 'bowl': 'bowl', 'spoon': 'spoon', 'fork': 'fork',
            'knife': 'knife', 'towel': 'towel',
            # Food items
            'pizza': 'pizza', 'burger': 'burger', 'sandwich': 'sandwich',
            'cake': 'cake', 'donut': 'donut', 'cookie': 'cookie',
            'ice cream': 'ice cream', 'coffee': 'coffee', 'tea': 'tea',
            # Animals
            'dog': 'dog', 'cat': 'cat', 'bird': 'bird', 'fish': 'fish',
            # Vehicles
            'car': 'car', 'bicycle': 'bicycle', 'motorcycle': 'motorcycle',
            'bus': 'bus', 'truck': 'truck', 'train': 'train'
        }
        
        print(f"[CNN] Detector ready using: {self.model_type.upper()}")
    
    def _load_yolo(self):
        """Load YOLOv8 model (better accuracy)"""
        try:
            # Try different YOLO versions
            models_to_try = ['yolov8n.pt', 'yolov8s.pt', 'yolo11n.pt']
            
            for model_name in models_to_try:
                try:
                    self.model = YOLO(model_name)
                    self.model_type = "yolo"
                    self.class_names = self.model.names
                    print(f"[CNN] YOLO model loaded: {model_name}")
                    return
                except Exception:
                    continue
            
            raise Exception("No YOLO model found")
        except Exception as e:
            print(f"[CNN] YOLO load failed: {e}")
            self._load_mobilenet()
    
    def _load_mobilenet(self):
        """Load MobileNetV2 model (fallback)"""
        self.model = MobileNetV2(weights='imagenet')
        self.model_type = "mobilenet"
        print("[CNN] MobileNetV2 model loaded")
    
    def detect(self, image_path: str, min_confidence: float = 0.25) -> Tuple[str, float]:
        """
        Detect object in image
        Returns: (item_name, confidence)
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Could not read image: {image_path}")
                return ("unknown", 0.0)
            
            start_time = time.time()
            
            if self.model_type == "yolo":
                # YOLO detection
                results = self.model(image_path, conf=min_confidence, verbose=False)
                detections = results[0].boxes
                
                if detections is None or len(detections) == 0:
                    return ("unknown", 0.0)
                
                # Get top detection
                top_box = detections[0]
                class_id = int(top_box.cls[0])
                confidence = float(top_box.conf[0])
                class_name = self.class_names[class_id].lower()
                
                # Map to friendly name
                friendly_name = self._map_object_name(class_name)
                
                elapsed = (time.time() - start_time) * 1000
                logger.debug(f"YOLO detection: {friendly_name} ({confidence:.2f}) - {elapsed:.0f}ms")
                
                return (friendly_name, confidence)
            
            else:
                # MobileNetV2 detection
                img = cv2.resize(img, (224, 224))
                img = preprocess_input(img)
                img = np.expand_dims(img, axis=0)
                
                predictions = self.model.predict(img, verbose=0)
                results = decode_predictions(predictions, top=3)[0]
                
                label = results[0][1].split(',')[0]
                confidence = results[0][2]
                label = label.lower().replace('_', ' ')
                
                friendly_name = self._map_object_name(label)
                
                elapsed = (time.time() - start_time) * 1000
                logger.debug(f"MobileNet detection: {friendly_name} ({confidence:.2f}) - {elapsed:.0f}ms")
                
                return (friendly_name, confidence)
                
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return ("error", 0.0)
    
    def detect_multiple(self, image_path: str, min_confidence: float = 0.25) -> List[Dict[str, Any]]:
        """
        Detect multiple objects in image
        Returns list of detected objects with their bounding boxes
        """
        try:
            if self.model_type != "yolo":
                # For MobileNet, just return top detection
                item, confidence = self.detect(image_path, min_confidence)
                return [{
                    'item': item,
                    'confidence': confidence,
                    'bbox': None
                }] if confidence > 0 else []
            
            # YOLO multi-object detection
            results = self.model(image_path, conf=min_confidence, verbose=False)
            detections = results[0].boxes
            
            if detections is None or len(detections) == 0:
                return []
            
            objects = []
            for box in detections:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = self.class_names[class_id].lower()
                bbox = box.xyxy[0].tolist()
                
                friendly_name = self._map_object_name(class_name)
                
                objects.append({
                    'item': friendly_name,
                    'confidence': confidence,
                    'bbox': bbox
                })
            
            # Sort by confidence
            objects.sort(key=lambda x: x['confidence'], reverse=True)
            return objects
            
        except Exception as e:
            logger.error(f"Multi-detection error: {e}")
            return []
    
    def detect_from_bytes(self, image_bytes: bytes, min_confidence: float = 0.25) -> Tuple[str, float]:
        """Detect object from raw image bytes"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        try:
            result = self.detect(tmp_path, min_confidence)
            return result
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def detect_multiple_from_bytes(self, image_bytes: bytes, min_confidence: float = 0.25) -> List[Dict[str, Any]]:
        """Detect multiple objects from raw image bytes"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        try:
            return self.detect_multiple(tmp_path, min_confidence)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def detect_batch(self, image_paths: List[str], min_confidence: float = 0.25) -> List[Tuple[str, float]]:
        """Detect objects in multiple images in parallel"""
        results = []
        
        def process_single(path):
            return self.detect(path, min_confidence)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(process_single, image_paths))
        
        return results
    
    def _map_object_name(self, name: str) -> str:
        """Map detected object name to inventory-friendly name"""
        name_lower = name.lower()
        
        # Direct mapping
        for key, value in self.name_map.items():
            if key in name_lower or name_lower in key:
                return value
        
        # Handle specific cases
        if 'bottle' in name_lower:
            return 'bottle'
        if 'phone' in name_lower or 'cell' in name_lower:
            return 'phone'
        if 'computer' in name_lower or 'laptop' in name_lower:
            return 'laptop'
        if 'book' in name_lower:
            return 'book'
        if 'chair' in name_lower:
            return 'chair'
        if 'table' in name_lower:
            return 'table'
        if 'cup' in name_lower or 'mug' in name_lower:
            return 'cup'
        if 'plate' in name_lower or 'dish' in name_lower:
            return 'plate'
        
        # Return cleaned name
        return name_lower.split()[0] if name_lower else 'item'
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            'model_type': self.model_type,
            'model_loaded': self.model is not None,
            'yolo_available': YOLO_AVAILABLE,
            'class_count': len(self.class_names) if self.class_names else 1000,
            'name_mappings': len(self.name_map)
        }

# Create singleton instance
detector = CNNDetector()

# Async wrapper for detection
async def detect_async(image_bytes: bytes) -> Tuple[str, float]:
    """Async wrapper for detection"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        detector.detect_from_bytes,
        image_bytes
    )

async def detect_multiple_async(image_bytes: bytes) -> List[Dict[str, Any]]:
    """Async wrapper for multiple detection"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        detector.detect_multiple_from_bytes,
        image_bytes
    )