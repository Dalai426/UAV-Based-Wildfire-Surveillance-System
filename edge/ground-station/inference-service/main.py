import os
from time import time
from inference import CustomModel

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2

URL = os.environ["RTSP_URL"]

cap = cv2.VideoCapture(URL)

while not cap.isOpened():
    print("Could not open video stream. Retrying in 5 seconds")
    time.sleep(5)
    cap = cv2.VideoCapture(URL)

net = CustomModel(weights_path=os.environ["MODEL_WEIGHTS_PATH"])

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        time.sleep(5)
        cap = cv2.VideoCapture(URL)
        continue

    prediction = net.predict(frame)
    print(prediction)


cap.release()
