# Image for the drone's simulated flight controller: ArduPilot SITL
# Two stages: "build" compiles ArduPilot with all compilers; "runtime" gets only the finished
# simulator and the Python tools to start it, so the compilers stay out of the final image
# Build it with `docker compose build` in edge/drone (see README.md)

# Stage 1: download and compile ArduPilot
FROM ubuntu:22.04 AS build

# A fixed release, so everyone on the team flies the same code
ARG ARDUPILOT_TAG=Copter-4.7.2

# Keeps apt from asking questions (e.g. the time zone) during the build
ARG DEBIAN_FRONTEND=noninteractive

# The minimum needed to download ArduPilot and run its install script
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git sudo lsb-release tzdata \
    && rm -rf /var/lib/apt/lists/*

# ArduPilot's install script refuses to run as root but needs sudo, so use a normal user
# that may use sudo without a password
RUN useradd --create-home --shell /bin/bash ardupilot \
    && echo "ardupilot ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ardupilot
USER ardupilot
WORKDIR /home/ardupilot

# Only the chosen release and its submodules, without history (saves several hundred MB)
RUN git clone --depth 1 --branch "${ARDUPILOT_TAG}" \
        --recurse-submodules --shallow-submodules \
        https://github.com/ArduPilot/ardupilot.git
WORKDIR /home/ardupilot/ardupilot

# Install the build tools, leaving out what a simulator doesn't need (graphical tools,
# coverage tools, the ARM compiler for real boards)
RUN SKIP_AP_EXT_ENV=1 SKIP_AP_GRAPHIC_ENV=1 SKIP_AP_COV_ENV=1 SKIP_AP_GIT_CHECK=1 \
    DO_AP_STM_ENV=0 AP_DOCKER_BUILD=1 USER=ardupilot \
    Tools/environment_install/install-prereqs-ubuntu.sh -y

# Compile the copter simulator (result: build/sitl/bin/arducopter). ~/.ardupilot_env holds
# the PATH settings the install script wrote
RUN bash -c "source ~/.ardupilot_env && ./waf configure --board sitl && ./waf copter"

# Stage 2: the small image that runs the simulator
FROM ubuntu:22.04 AS runtime

ARG DEBIAN_FRONTEND=noninteractive

# Python for the launcher (sim_vehicle.py) and MAVProxy, which forwards the telemetry
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# MAVProxy needs pymavlink (MAVLink), pyserial (imported at start) and pexpect (used by
# sim_vehicle.py). --no-deps skips MAVProxy's map and graph libraries, which made the
# image 1.75 GB and are never used without a screen
RUN pip3 install --no-cache-dir pymavlink pyserial pexpect \
    && pip3 install --no-cache-dir --no-deps MAVProxy

# The simulator runs as a normal user, not as root
RUN useradd --create-home --shell /bin/bash drone

# From stage 1: the compiled simulator, and Tools/autotest (sim_vehicle.py, its helpers and the
# default copter settings). sim_vehicle.py finds them through ArduPilot's folder layout
COPY --from=build /home/ardupilot/ardupilot/build/sitl/bin/arducopter /ardupilot/build/sitl/bin/arducopter
COPY --from=build /home/ardupilot/ardupilot/Tools/autotest /ardupilot/Tools/autotest

COPY start_sitl.sh /usr/local/bin/start_sitl.sh

# The flight path and the script that flies it on every start. COPY creates /missions
COPY --chown=root:drone --chmod=0640 flight.plan /missions/flight.plan
RUN chown root:drone /missions && chmod 0750 /missions
COPY fly_mission.py /usr/local/bin/fly_mission.py

# Mavic Air battery drain. It goes in the working folder: the simulator only loads relative paths
COPY mavic-battery.json /ardupilot/ArduCopter/mavic-battery.json

# sim_vehicle.py needs a folder named after the vehicle; the simulator writes its settings
# (eeprom.bin) and flight logs there
RUN mkdir -p /ardupilot/ArduCopter && chown -R drone:drone /ardupilot/ArduCopter

USER drone
WORKDIR /ardupilot/ArduCopter
ENV PATH="/ardupilot/Tools/autotest:${PATH}"

CMD ["start_sitl.sh"]
