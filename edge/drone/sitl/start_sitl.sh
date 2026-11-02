#!/usr/bin/env bash
# Runs INSIDE the sitl container and starts the drone's simulated flight controller.
#
# sim_vehicle.py is ArduPilot's launcher. It starts two programs:
#   - arducopter: the simulated flight controller itself
#   - MAVProxy:   a small text-based ground station that forwards the telemetry (MAVLink) to
#                 the ground station on the Mac
#
# Settings come from environment variables, which compose.yml fills in from .env.
set -euo pipefail

GROUND_HOST="${GROUND_HOST:-host.docker.internal}" # the ground station, as seen from the container
HOME_LOCATION="${HOME_LOCATION:-55.7670,12.3830,40,0}" # start position: lat,lon,altitude (m),heading
QGC_PORT=14550  # QGroundControl on the Mac (only needed for now, see README.md)
CORE_PORT=14551 # the ground station core's telemetry receiver

echo "Starting ArduCopter SITL at $HOME_LOCATION, sending MAVLink to $GROUND_HOST:$QGC_PORT and :$CORE_PORT"

# -v ArduCopter -f quad       simulate a quadcopter
# --custom-location           where the drone starts
# --no-rebuild                don't compile: the image already contains the compiled simulator
# -w                          reset all settings to ArduPilot's defaults, so every run starts the same
# --no-extra-ports            don't add the default output to 127.0.0.1:14550 (leads nowhere in a container)
# --out=udp:HOST:PORT         send MAVLink to HOST:PORT (and receive the replies on the same connection)
# exec                        replace this script with sim_vehicle.py, so `docker stop` reaches it directly
exec sim_vehicle.py \
    -v ArduCopter -f quad \
    --custom-location="$HOME_LOCATION" \
    --no-rebuild \
    -w \
    --no-extra-ports \
    --out="udp:$GROUND_HOST:$QGC_PORT" \
    --out="udp:$GROUND_HOST:$CORE_PORT"
