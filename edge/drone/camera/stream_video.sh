#!/usr/bin/env bash
# Safety settings: stop on problems instead of carrying on silently.
# -e           if a command fails (e.g. the video is missing or ffmpeg can't connect to MediaMTX),
#              the script stops with an error code. Docker sees that code and restarts the camera
#              (restart: on-failure in compose.yml).
# -u           using a variable that was never set (e.g. a typo like $STREAM_KYE) stops the script
#              instead of quietly using empty text. Optional settings have a default, e.g.
#              ${STREAM_KEY:-d7f3a91c}, so they never trigger this.
# -o pipefail  a pipe fails if any part of it fails. Needed for "ffmpeg ... | print_progress"
#              below: without it, a failing ffmpeg would be hidden behind the filter's success,
#              and Docker would not restart the camera.
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

# Short start message, e.g. "Streaming zenmuse.mp4 at 4M to host.docker.internal:8554/d7f3a91c (MediaMTX)"
echo "Streaming $(basename "$VIDEO") at $BITRATE to $GROUND:$RTSP_PORT/$STREAM_KEY (MediaMTX)"

# Turns ffmpeg's progress reports into one short log line each.
print_progress() {
    awk -F= '
        { gsub(/ /, "", $2); value[$1] = $2 }   # remember each key=value (spaces removed)
        $1 == "progress" {                      # end of one report: print the summary
            printf "time=%s frame=%s fps=%s dropped=%s duplicated=%s speed=%s\n",
                substr(value["out_time"], 1, 8), value["frame"], value["fps"],
                value["drop_frames"], value["dup_frames"], value["speed"]
            fflush()
        }'
}

# -re                      read at native speed, like a live camera
# -r 30                    constant 30 FPS like a real drone camera (zenmuse.mp4 has a variable frame rate;
#                          without this, ffmpeg would pad it to 120 FPS)
# -tune zerolatency        no B-frames / lookahead, as on-drone encoders do
# -g 30 -sc_threshold 0    a keyframe every ~1 s, so a new reader (e.g. a restarted AI container)
#                          can start decoding quickly, and the stream recovers quickly after errors
# -maxrate/-bufsize        cap the bitrate like a radio link would
# -rtsp_transport tcp      send the video over TCP; MediaMTX only accepts TCP (rtspTransports in mediamtx.yml)
# -f rtsp                  publish the stream to the RTSP server at STREAM_URL
# -nostats                 no overwriting progress line (see print_progress above)
# -progress pipe:1         write progress reports to stdout, which goes to print_progress
# -stats_period 5          one progress report every 5 seconds
#
# Warnings and errors still go to stderr, straight into the log.
# If ffmpeg fails, "set -o pipefail" makes the whole pipe fail, so the script exits with an
# error and Docker restarts the camera (restart: on-failure in compose.yml).
ffmpeg -hide_banner -loglevel warning -nostats -progress pipe:1 -stats_period 5 \
    -re -i "$VIDEO" \
    -map 0:v:0 -an -r 30 \
    -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
    -b:v "$BITRATE" -maxrate "$BITRATE" -bufsize "$BITRATE" \
    -g 30 -keyint_min 30 -sc_threshold 0 \
    -rtsp_transport tcp \
    -f rtsp "$STREAM_URL" \
    | print_progress
