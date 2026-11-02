#!/usr/bin/env bash
# Plays the role of the drone's camera + video encoder. Runs inside the "camera" container
# (see compose.yml and README.md).
# Re-encodes the video live as H.264 at a drone-typical bitrate and publishes it over RTSP
# to the ground station's media server (MediaMTX). One stream only, like a real drone.
# MediaMTX records it and passes it on to everyone who reads it (AI inference, QGroundControl, VLC).
#
# Usage: ./stream_video.sh [video_file] [bitrate]
#   e.g. ./stream_video.sh /videos/zenmuse.mp4 4M
set -euo pipefail

VIDEO="${1:-/videos/zenmuse.mp4}"
BITRATE="${2:-4M}"                 # typical drone downlinks: 2-8 Mbit/s
GROUND="${GROUND:-host.docker.internal}" # the ground station: the computer the containers run on
RTSP_PORT=8554                     # MediaMTX's RTSP port (see edge/ground-station/compose.yml)
STREAM_KEY="${STREAM_KEY:-d7f3a91c}" # MediaMTX path for this drone; must match STREAM_KEY in edge/ground-station/.env
STREAM_URL="rtsp://$GROUND:$RTSP_PORT/$STREAM_KEY"

if ! command -v ffmpeg >/dev/null; then
    echo "ffmpeg not found. Install it with: sudo apt install -y ffmpeg" >&2
    exit 1
fi
if [ ! -f "$VIDEO" ]; then
    echo "Video not found: $VIDEO" >&2
    exit 1
fi

echo "Streaming $VIDEO at $BITRATE -> MediaMTX on $STREAM_URL"

# -re                      read at native speed, like a live camera
# -r 30                    constant 30 FPS like a real drone camera (zenmuse.mp4 has a variable frame rate;
#                          without this, ffmpeg would pad it to 120 FPS)
# -tune zerolatency        no B-frames / lookahead, as on-drone encoders do
# -g 30 -sc_threshold 0    a keyframe every ~1 s, so a new reader (e.g. a restarted AI container)
#                          can start decoding quickly, and the stream recovers quickly after errors
# -maxrate/-bufsize        cap the bitrate like a radio link would
# -rtsp_transport tcp      send the video over TCP; MediaMTX only accepts TCP (rtspTransports in mediamtx.yml)
# -f rtsp                  publish the stream to the RTSP server at STREAM_URL
ffmpeg -hide_banner -loglevel warning -stats \
    -re -i "$VIDEO" \
    -map 0:v:0 -an -r 30 \
    -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
    -b:v "$BITRATE" -maxrate "$BITRATE" -bufsize "$BITRATE" \
    -g 30 -keyint_min 30 -sc_threshold 0 \
    -rtsp_transport tcp \
    -f rtsp "$STREAM_URL"
