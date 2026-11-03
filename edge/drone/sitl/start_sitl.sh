#!/usr/bin/env bash
# Runs INSIDE the sitl container and starts the drone's simulated flight controller.
#
# Safety settings: stop on problems instead of carrying on silently.
# -e           if a command fails, the script stops with an error code
#              (Docker then restarts the flight controller: restart: unless-stopped in compose.yml).
# -u           using a variable that was never set (e.g. a typo like $HOME_LOCATON) stops the script.
#              Optional settings have a default, e.g. ${GROUND_HOST:-host.docker.internal}.
# -o pipefail  a pipe fails if any part of it fails (no pipe here; kept so both scripts behave the same).
set -euo pipefail

GROUND_HOST="${GROUND_HOST:-host.docker.internal}" # the ground station, as seen from the container
HOME_LOCATION="${HOME_LOCATION:-55.7670,12.3830,40,0}" # start position: lat,lon,altitude (m),heading
QGC_PORT=14550  # QGroundControl (only needed for now, see README.md)
CORE_PORT=14551 # the ground station core's telemetry receiver

echo "Starting ArduCopter SITL at $HOME_LOCATION, sending MAVLink to $GROUND_HOST:$QGC_PORT and :$CORE_PORT"

# Fly the flight path automatically on every start.
# fly_mission.py runs in the background: it waits for the simulator started below, then
# uploads flight.plan and starts it. flight.plan is a QGroundControl plan file: edit it in
# QGroundControl and save it back. Its waypoints are fixed GPS coordinates around the
# default HOME_LOCATION.
echo "Mission: flight.plan (flown automatically)"
python3 /usr/local/bin/fly_mission.py /missions/flight.plan &

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
