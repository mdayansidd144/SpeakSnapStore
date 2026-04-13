
from fastapi import APIRouter, UploadFile, File
from ai_models.cnn_detector import detector
import tempfile
import os
import cv2

router = APIRouter()

# Constants for video processing
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FRAMES = 300  # Max frames to process

@router.post("/detect")
async def detect_object(image: UploadFile = File(...)):
    """Detect object from camera image"""
    try:
        content = await image.read()
        
        if not content:
            return {"success": False, "error": "Empty image", "detected_item": "unknown", "confidence": 0}
        
        print(f"[Vision] Received image: {len(content)} bytes")
        
        item, confidence = detector.detect_from_bytes(content)
        
        print(f"[Vision] Detection result: {item} ({confidence:.2f})")
        
        return {
            "detected_item": item,
            "confidence": float(confidence),
            "success": True
        }
    except Exception as e:
        print(f"[Vision] Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "detected_item": "error",
            "confidence": 0
        }

@router.post("/detect-video")
async def detect_video(video: UploadFile = File(...)):
    """Detect objects from video file (MP4, AVI, MOV)"""
    tmp_path = None
    try:
        content = await video.read()
        
        # Check file size
        if len(content) > MAX_VIDEO_SIZE:
            return {"success": False, "error": f"Video too large (max {MAX_VIDEO_SIZE//(1024*1024)}MB)", "detections": []}
        
        # Save uploaded video temporarily
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        print(f"[Vision] Saved video: {tmp_path}")
        print(f"[Vision] Video size: {len(content)} bytes")
        
        # Open video with OpenCV
        cap = cv2.VideoCapture(tmp_path)
        
        if not cap.isOpened():
            return {"success": False, "error": "Could not open video file", "detections": []}
        
        # Get video info
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"[Vision] Video FPS: {fps}, Total frames: {total_frames}")
        
        # Process every N frames (skip for speed)
        frame_skip = max(1, int(fps / 2))  # Process 2 frames per second
        frame_count = 0
        detected_items = {}
        
        while frame_count < MAX_FRAMES:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process every Nth frame
            if frame_count % frame_skip == 0:
                # Save frame as temp image
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as img_tmp:
                    cv2.imwrite(img_tmp.name, frame)
                    
                    # Read and detect using consistent method
                    with open(img_tmp.name, 'rb') as f:
                        img_bytes = f.read()
                    item, confidence = detector.detect_from_bytes(img_bytes)
                    
                    # Clean up
                    os.unlink(img_tmp.name)
                    
                    if item != "unknown" and confidence > 0.3:
                        if item not in detected_items:
                            detected_items[item] = {
                                'item': item,
                                'confidence': confidence,
                                'first_seen': frame_count
                            }
                        else:
                            if confidence > detected_items[item]['confidence']:
                                detected_items[item]['confidence'] = confidence
            
            frame_count += 1
        
        cap.release()
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        detections_list = list(detected_items.values())
        
        print(f"[Vision] Detected {len(detections_list)} unique objects")
        
        return {
            "success": True,
            "detections": detections_list,
            "total_frames": frame_count,
            "message": f"Detected {len(detections_list)} objects in video"
        }
        
    except Exception as e:
        print(f"[Vision] Error: {e}")
        import traceback
        traceback.print_exc()
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass
        return {"success": False, "error": str(e), "detections": []}

@router.get("/test")
async def test_detection():
    """Test if vision API is working"""
    return {"status": "ok", "message": "Vision API with YOLO is working"}