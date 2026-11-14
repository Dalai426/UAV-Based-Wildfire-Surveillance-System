# Image for the drone's simulated flight controller: ArduPilot SITL ("Software In The Loop").
#
# Built in two stages:
#   1. "build":   a large workshop image with all compilers. It downloads ArduPilot and compiles
#                 the copter simulator once.
#   2. "runtime": a small image that only gets the finished simulator plus the Python tools
#                 needed to start it. The compilers stay behind in stage 1.
#
# Build it with `docker compose build` in edge/drone (see README.md).

# Stage 1: download and compile ArduPilot
FROM ubuntu:22.04 AS build

# The ArduPilot release to build. A fixed release means everyone on the team flies the same code.
ARG ARDUPILOT_TAG=Copter-4.7.2

# Keeps apt from stopping to ask questions (e.g. the time zone) during the build.
ARG DEBIAN_FRONTEND=noninteractive

# The minimum needed to download ArduPilot and run its install script.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git sudo lsb-release tzdata \
    && rm -rf /var/lib/apt/lists/*

# ArduPilot's install script refuses to run as root, but it needs sudo to install packages.
# So we create a normal user that may use sudo without a password.
RUN useradd --create-home --shell /bin/bash ardupilot \
    && echo "ardupilot ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ardupilot
USER ardupilot
WORKDIR /home/ardupilot

# Download only the chosen release (--depth 1) and the submodules it needs (libraries such as
# MAVLink), without their full history. This saves several hundred megabytes.
RUN git clone --depth 1 --branch "${ARDUPILOT_TAG}" \
        --recurse-submodules --shallow-submodules \
        https://github.com/ArduPilot/ardupilot.git
WORKDIR /home/ardupilot/ardupilot

# Install ArduPilot's build tools. The SKIP_/DO_ switches leave out what a simulator doesn't need:
# graphical tools, coverage tools and the ARM compiler for real flight controller boards.
# AP_DOCKER_BUILD=1 tells the script that it runs inside a Docker build.
RUN SKIP_AP_EXT_ENV=1 SKIP_AP_GRAPHIC_ENV=1 SKIP_AP_COV_ENV=1 SKIP_AP_GIT_CHECK=1 \
    DO_AP_STM_ENV=0 AP_DOCKER_BUILD=1 USER=ardupilot \
    Tools/environment_install/install-prereqs-ubuntu.sh -y

# Compile the copter simulator for SITL. The install script wrote its settings (PATH etc.) to
# ~/.ardupilot_env, so we load them first. Result: build/sitl/bin/arducopter
RUN bash -c "source ~/.ardupilot_env && ./waf configure --board sitl && ./waf copter"

# Stage 2: the small image that actually runs the simulator
FROM ubuntu:22.04 AS runtime

ARG DEBIAN_FRONTEND=noninteractive

# Python is needed for the launcher (sim_vehicle.py) and for MAVProxy, the small text-based
# ground station that forwards the telemetry to the ground station.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# MAVProxy, plus what it needs without a screen:
#   pymavlink  the MAVLink library
#   pyserial   serial ports (MAVProxy imports it at start)
#   pexpect    used by sim_vehicle.py to start and watch its programs
#
# MAVProxy is installed with --no-deps on purpose: its normal dependencies include the
# libraries for its map and graph windows (VTK, OpenCV, matplotlib), which made this image
# 1.75 GB. A headless simulator never opens those windows.
RUN pip3 install --no-cache-dir pymavlink pyserial pexpect \
    && pip3 install --no-cache-dir --no-deps MAVProxy

# The simulator runs as a normal user, not as root: a container should have no more rights than
# it needs.
RUN useradd --create-home --shell /bin/bash drone

# From stage 1 we take only:
#   - the compiled copter simulator
#   - Tools/autotest: sim_vehicle.py, its helper modules and the default copter parameters
# sim_vehicle.py finds them through the folder layout, so we keep ArduPilot's layout under /ardupilot.
COPY --from=build /home/ardupilot/ardupilot/build/sitl/bin/arducopter /ardupilot/build/sitl/bin/arducopter
COPY --from=build /home/ardupilot/ardupilot/Tools/autotest /ardupilot/Tools/autotest

# Our start script (see start_sitl.sh for the options it uses).
COPY start_sitl.sh /usr/local/bin/start_sitl.sh

# The flight path (flown automatically on every start) and the script that flies it.
COPY flight.plan /missions/flight.plan
COPY fly_mission.py /usr/local/bin/fly_mission.py

# The simulator model that gives the drone the battery drain of a DJI Mavic Air.
# It goes in the simulator's working folder, because the simulator only loads relative paths.
COPY mavic-battery.json /ardupilot/ArduCopter/mavic-battery.json

# sim_vehicle.py expects a folder named after the vehicle. The simulator also writes its
# settings (eeprom.bin) and flight logs there.
RUN mkdir -p /ardupilot/ArduCopter && chown -R drone:drone /ardupilot/ArduCopter

USER drone
WORKDIR /ardupilot/ArduCopter
ENV PATH="/ardupilot/Tools/autotest:${PATH}"

CMD ["start_sitl.sh"]
