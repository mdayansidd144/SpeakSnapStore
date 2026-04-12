import cv2
import numpy as np
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions

# Load model
model = MobileNetV2(weights='imagenet')
print("Model loaded successfully!")

# Try with a test image (create a sample)
test_img = np.random.rand(224, 224, 3) * 255
test_img = test_img.astype(np.uint8)
test_img = preprocess_input(test_img)
test_img = np.expand_dims(test_img, axis=0)

predictions = model.predict(test_img)
results = decode_predictions(predictions, top=3)[0]
print("Test prediction:", results)