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

while not cap.isOpened():
    print("Could not open video stream. Retrying in 5 seconds")
    time.sleep(5)
    cap = cv2.VideoCapture(URL)

net = CustomModel(weights_path=os.environ["MODEL_WEIGHTS_PATH"])

streamFps = cap.get(cv2.CAP_PROP_FPS)
TARGET_FPS = 5
MAX_SKIPPED_FRAMES = 10
TIMEOUT_MS = 5000

frameCount = 0
skippedFramesCount = 0

def openStream(url):
    return cv2.VideoCapture(
        url,
        [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            TIMEOUT_MS,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            TIMEOUT_MS,
        ],
    )

while True:
    grabbed = cap.grab()

    if not grabbed:
        print("Failed to capture frame", flush=True)
        time.sleep(5)
        cap.release()
        cap = openStream(URL)
        continue

    frameCount += 1

    if frameCount % (streamFps // TARGET_FPS) == 0:
        ret, frame = cap.retrieve()
        if not ret:
            print("Failed to retrieve frame", flush=True)
            skippedFramesCount += 1
            if skippedFramesCount >= MAX_SKIPPED_FRAMES:
                print("Too many skipped frames. Reconnecting to stream.", flush=True)
                cap.release()
                cap = openStream(URL)
                skippedFramesCount = 0
            continue

        skippedFramesCount = 0
        prediction = net.predict(frame)
        #timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
        timestampStart = datetime.now(timezone.utc) - timedelta(seconds=5)
        timestampEnd =  datetime.now(timezone.utc)

        if prediction >= 0:
            print(frameCount, " : ", prediction, " : ", timestampStart, " : ", timestampEnd, flush=True)
            response = requests.post("http://ground-station-core:8080/events", json={"start": timestampStart.isoformat(), "end": timestampEnd.isoformat(), "confidence": prediction})
            print(response.status_code, response.text, flush=True)



cap.release()
