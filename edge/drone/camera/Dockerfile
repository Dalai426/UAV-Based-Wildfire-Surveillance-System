# Image for the drone's simulated camera: a small Linux with ffmpeg that runs camera_control.py, which starts stream_video.sh while the drone is armed
# Alpine Linux is used because it is tiny 
# ffmpeg package includes the libx264 H.264 encoder that stream_video.sh uses
# bash is added because the script is a bash script
# python3 is added for the script that reads the drone's state over MAVLink    
FROM alpine:3.20

RUN apk add --no-cache bash ffmpeg python3

# pymavlink reads the drone's MAVLink messages. Alpine's pip refuses to install into the
# system Python, so it goes into its own virtual environment in /opt/venv
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir pymavlink

# The camera runs as a normal user, not as root
RUN adduser -D camera

# Copy the script into the image, so the image works on its own (e.g. later on a Raspberry Pi)
COPY stream_video.sh camera_control.py /usr/local/bin/

USER camera

# compose.yml passes the video file and the bitrate as arguments
# camera_control.py passes them on to stream_video.sh
ENTRYPOINT ["/opt/venv/bin/python", "/usr/local/bin/camera_control.py"]
