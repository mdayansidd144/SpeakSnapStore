import cv2
import numpy as np
import tempfile
import os
from ultralytics import YOLO
import torch

class CNNDetector:
    def __init__(self):
        print("[CNN] Loading YOLOv11 model...")
        # Load YOLOv11 medium model (best balance for accuracy/speed)
        self.model = YOLO('yolo11m.pt')
        
        # Set model to evaluation mode
        self.model.eval()
        
        # Check if GPU is available
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[CNN] Using device: {self.device}")
        
        # Move model to GPU if available
        if self.device == 'cuda':
            self.model.to('cuda')
        
        print("[CNN] YOLOv11 model loaded successfully!")
        
        # Extended mapping for inventory-friendly names
        self.name_map = {
            # Fruits
            'apple': 'apple', 'banana': 'banana', 'orange': 'orange',
            'strawberry': 'strawberry', 'grape': 'grape', 'watermelon': 'watermelon',
            # Electronics
            'laptop': 'laptop', 'cell phone': 'phone', 'smartphone': 'phone',
            'keyboard': 'keyboard', 'mouse': 'mouse', 'monitor': 'monitor',
            # Stationery
            'book': 'book', 'notebook': 'notebook', 'pen': 'pen', 'pencil': 'pencil',
            # Household
            'bottle': 'bottle', 'cup': 'cup', 'chair': 'chair', 'table': 'table',
            # Food items
            'pizza': 'pizza', 'burger': 'burger', 'sandwich': 'sandwich',
            'cake': 'cake', 'donut': 'donut', 'cookie': 'cookie'
        }
    
    def detect(self, image_path: str) -> tuple:
        """Detect object in image using YOLOv11 and return (item_name, confidence)"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                print(f"[CNN] Error: Could not read image from {image_path}")
                return ("unknown", 0.0)
            
            print(f"[CNN] Image shape: {img.shape}")
            
            # Run inference with YOLOv11
            results = self.model(image_path, conf=0.25, iou=0.45)
            
            # Get detections
            detections = results[0].boxes
            if detections is None or len(detections) == 0:
                print("[CNN] No objects detected")
                return ("unknown", 0.0)
            
            # Get top detection (highest confidence)
            top_box = detections[0]
            class_id = int(top_box.cls[0])
            confidence = float(top_box.conf[0])
            
            # Get class name from YOLO
            class_name = self.model.names[class_id].lower()
            
            print(f"[CNN] YOLOv11 detected: {class_name} (confidence: {confidence:.4f})")
            
            # Map to friendly name if available
            if class_name in self.name_map:
                friendly_name = self.name_map[class_name]
                print(f"[CNN] Mapped to: {friendly_name}")
                return (friendly_name, confidence)
            
            # Return the detected class name directly
            return (class_name, confidence)
            
        except Exception as e:
            print(f"[CNN] Error in detect: {e}")
            import traceback
            traceback.print_exc()
            return ("error", 0.0)
    
    def detect_multiple(self, image_path: str, min_confidence: float = 0.25) -> list:
        """Detect multiple objects in image and return list of items"""
        try:
            results = self.model(image_path, conf=min_confidence, iou=0.45)
            detections = results[0].boxes
            
            if detections is None or len(detections) == 0:
                return []
            
            detected_items = []
            for box in detections:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = self.model.names[class_id].lower()
                
                # Map to friendly name
                friendly_name = self.name_map.get(class_name, class_name)
                
                detected_items.append({
                    'item': friendly_name,
                    'confidence': confidence,
                    'bbox': box.xyxy[0].tolist()
                })
            
            return detected_items
            
        except Exception as e:
            print(f"[CNN] Error in detect_multiple: {e}")
            return []
    
    def detect_from_bytes(self, image_bytes: bytes) -> tuple:
        """Detect object from raw image bytes"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            
            print(f"[CNN] Saved temp image: {tmp_path}")
            print(f"[CNN] Image size: {len(image_bytes)} bytes")
            
            # Run detection
            result = self.detect(tmp_path)
            
            # Clean up
            os.unlink(tmp_path)
            return result
            
        except Exception as e:
            print(f"[CNN] Error in detect_from_bytes: {e}")
            return ("error", 0.0)

# Create singleton instance
detector = CNNDetector()