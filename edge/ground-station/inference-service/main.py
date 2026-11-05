import os
import time
from inference import CustomModel

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
flag = False

while cap.isOpened():
    ret, frame = cap.read()
    if flag:
        continue 

    if not ret:
        print("Failed to capture frame")
        time.sleep(5)
        cap = cv2.VideoCapture(URL)
        continue


    frameCount += 1
    if frameCount % (streamFps // TARGET_FPS)  == 0:
        prediction = net.predict(frame)
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)

        if prediction >= 0:
            print(frameCount, " : ", prediction, " : ", timestamp, flush=True)
            response = requests.post("http://ground-station-core:8080/events", json={"start": timestamp, "end": timestamp+1})
            print(response.status_code, response.text, flush=True)


    #flag = True


cap.release()
