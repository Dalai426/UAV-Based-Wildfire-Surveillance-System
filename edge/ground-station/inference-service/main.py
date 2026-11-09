import os
import time
from inference import CustomModel
from datetime import datetime, timezone, timedelta

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2
import requests

URL = os.environ["RTSP_URL"]
print("url: ", URL, flush=True)

cap = cv2.VideoCapture(URL)

streamFps = cap.get(cv2.CAP_PROP_FPS)
TARGET_FPS = 5

while not cap.isOpened():
    print("Could not open video stream. Retrying in 5 seconds")
    time.sleep(5)
    cap = cv2.VideoCapture(URL)

net = CustomModel(weights_path=os.environ["MODEL_WEIGHTS_PATH"])

frameCount = 0

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        print("Failed to capture frame", flush=True)
        time.sleep(5)
        cap = cv2.VideoCapture(URL)
        continue


    frameCount += 1
    if frameCount % (streamFps // TARGET_FPS)  == 0:
        prediction = net.predict(frame)
        #timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
        timestampStart = datetime.now(timezone.utc) - timedelta(seconds=5)
        timestampEnd =  datetime.now(timezone.utc)

        if prediction >= 0:
            print(frameCount, " : ", prediction, " : ", timestampStart, " : ", timestampEnd, flush=True)
            response = requests.post("http://ground-station-core:8080/events", json={"start": timestampStart.isoformat(), "end": timestampEnd.isoformat(), "confidence": prediction})
            print(response.status_code, response.text, flush=True)



cap.release()
