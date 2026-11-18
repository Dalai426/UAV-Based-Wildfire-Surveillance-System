import os
import time
from collections import deque
from inference import CustomModel
from datetime import datetime, timezone

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

# A frame counts as fire when the model's probability is above this
FIRE_THRESHOLD = 0.5
# Fire is only reported when at least CONFIRM_MIN of the last
# CONFIRM_WINDOW predictions are above the threshold, so a single
# flickering frame does not raise an alert
CONFIRM_WINDOW = 5
CONFIRM_MIN = 3
MAX_SKIPPED_FRAMES = 10
TIMEOUT_MS = 5000

frameCount = 0
skippedFramesCount = 0

# The last predictions as (grab time, probability)
recent = deque(maxlen=CONFIRM_WINDOW)

def openStream(url):
    # With a list of settings, OpenCV also needs the backend (FFmpeg reads RTSP)
    return cv2.VideoCapture(
        url,
        cv2.CAP_FFMPEG,
        [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            TIMEOUT_MS,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            TIMEOUT_MS,
        ],
    )

while True:
    grabbed = cap.grab()
    # Detection time X: when this frame was read from the stream,
    # before decoding and prediction add their delay
    grabTime = datetime.now(timezone.utc)

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
        probability = net.predict(frame)
        #timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
        recent.append((grabTime, probability))
        fireFrames = [(t, p) for t, p in recent if p > FIRE_THRESHOLD]

        if len(fireFrames) >= CONFIRM_MIN:
            # X is the oldest fire frame in the window: when the fire was first seen
            detectionTime, confidence = fireFrames[0]
            print(frameCount, " : ", confidence, " : ", detectionTime, flush=True)
            # Report the detection; the Core picks the clip and the drone's position at X
            response = requests.post("http://ground-station-core:8080/events", json={"detection_time": detectionTime.isoformat(), "confidence_percent": confidence * 100})
            print(response.status_code, response.text, flush=True)



cap.release()
