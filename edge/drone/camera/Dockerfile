# Image for the drone's simulated camera: a small Linux with ffmpeg that runs stream_video.sh.
#
# Alpine Linux is used because it is tiny. Its ffmpeg package includes the libx264 H.264 encoder
# that stream_video.sh uses. bash is added because the script is a bash script.
#
# Build it with `docker compose build` in edge/drone. The build context is edge/drone (set in
# compose.yml), so stream_video.sh can be copied in from there.
FROM alpine:3.20

RUN apk add --no-cache bash ffmpeg

# The camera runs as a normal user, not as root.
RUN adduser -D camera

# Copy the script into the image, so the image works on its own (e.g. later on a Raspberry Pi).
COPY stream_video.sh /usr/local/bin/stream_video.sh

USER camera

# compose.yml passes the video file and the bitrate as arguments.
ENTRYPOINT ["stream_video.sh"]
