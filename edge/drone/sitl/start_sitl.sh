#!/usr/bin/env bash

# Safety settings:
# -e           if a command fails, the script stops with an error code
# -u           using a variable that was never set stops the script.
set -eu

HOME_LOCATION="55.7670,12.3830,40,0" # start position
QGC_PORT=14550  # QGroundControl
CORE_PORT=14551 # the ground station core's telemetry receiver

echo "Starting ArduCopter SITL at $HOME_LOCATION, sending MAVLink to $GROUND_HOST:$QGC_PORT and :$CORE_PORT"

# Fly the flight path automatically on every start.
python3 /usr/local/bin/fly_mission.py /missions/flight.plan &

# -v ArduCopter -f quad       simulate a quadcopter
# --model +:FILE              a + frame quad using the battery values in FILE
# --custom-location           where the drone starts
# --no-rebuild                don't compile: the image already contains the compiled simulator
# -w                          reset all settings to ArduPilot's defaults, so every run starts the same
# --no-extra-ports            don't add the default output to 127.0.0.1:14550 (leads nowhere in a container)
# --out=udp:HOST:PORT         send MAVLink to HOST:PORT (and receive the replies on the same connection)
# exec                        replace this script with sim_vehicle.py, so `docker stop` reaches it directly
exec sim_vehicle.py \
    -v ArduCopter -f quad \
    --model "+:mavic-battery.json" \
    --custom-location="$HOME_LOCATION" \
    --no-rebuild \
    -w \
    --no-extra-ports \
    --out="udp:$GROUND_HOST:$QGC_PORT" \
    --out="udp:$GROUND_HOST:$CORE_PORT"
