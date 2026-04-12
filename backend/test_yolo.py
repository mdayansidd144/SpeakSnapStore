from ultralytics import YOLO
import cv2

# Load model
model = YOLO('yolo26n.pt')
print("Model loaded successfully!")

# Test on sample image (download a test image or use camera)
# For webcam test:
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

if ret:
    cv2.imwrite("test.jpg", frame)
    results = model("test.jpg")
    results[0].show()
    print("Detection completed! Check the popup window.")
else:
    print("Could not capture from camera")