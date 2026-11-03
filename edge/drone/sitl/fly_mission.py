"""
Flies a mission automatically: runs INSIDE the sitl container, next to the simulator.

Started by start_sitl.sh on every start of the drone. It
  1. connects to the simulated flight controller,
  2. uploads the flight plan,
  3. waits until the drone is ready to fly (GPS and position estimate),
  4. switches to AUTO, arms the motors and lets the mission run,
  5. logs the progress and, after landing, how long the flight took.

The flight plan is a QGroundControl .plan file, so it can be edited in QGroundControl
and saved straight back, without converting it.

Usage: python3 fly_mission.py /missions/flight.plan
"""

import json
import sys
import time

from pymavlink import mavutil


# The simulator's second connection (TCP 5762). The first one (5760) is used by
# MAVProxy, which forwards the telemetry to QGroundControl and the ground station.
CONNECTION = "tcp:127.0.0.1:5762"

# AUTO_OPTIONS bits 0 + 1: allow arming in AUTO mode and taking off without a pilot
# raising the throttle stick (there is no pilot in the simulation).
AUTO_OPTIONS = 3


def log(message):
    print(f"mission: {message}", flush=True)


def connect():
    """Connect to the flight controller, waiting until the simulator is up."""
    while True:
        try:
            link = mavutil.mavlink_connection(CONNECTION, source_system=250)
            if link.wait_heartbeat(timeout=10):
                return link
        except OSError:
            pass   # simulator not started yet
        time.sleep(2)


def set_parameter(link, name, value):
    link.mav.param_set_send(link.target_system, link.target_component, name.encode(),
                            value, mavutil.mavlink.MAV_PARAM_TYPE_INT32)
    while True:
        reply = link.recv_match(type="PARAM_VALUE", blocking=True, timeout=5)
        if reply is None or reply.param_id == name:
            return


def request_messages(link, rate_hz=1):
    """Ask the flight controller to send the messages this script waits for on its connection."""
    for message_id in (mavutil.mavlink.MAVLINK_MSG_ID_SYS_STATUS,      # pre-arm checks passed?
                       mavutil.mavlink.MAVLINK_MSG_ID_SYSTEM_TIME,     # the drone's clock
                       mavutil.mavlink.MAVLINK_MSG_ID_MISSION_CURRENT):  # mission progress
        link.mav.command_long_send(link.target_system, link.target_component,
                                   mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
                                   message_id, 1_000_000 / rate_hz, 0, 0, 0, 0, 0)


def load_plan(path):
    """
    Read a QGroundControl .plan file and return the mission as a list of items.

    Each item is (frame, command, auto_continue, params), with the seven MAVLink
    params: p1-p4, latitude, longitude, altitude. Item 0 is the home position, as
    ArduPilot expects.

    QGroundControl's pattern tools (e.g. Survey, Corridor Scan) store their flight lines
    as one "ComplexItem"; the individual waypoints are inside it and are unpacked here.
    """
    mission = json.loads(open(path).read())["mission"]

    home_lat, home_lon, home_alt = mission["plannedHomePosition"]
    items = [(mavutil.mavlink.MAV_FRAME_GLOBAL, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, True,
              [0, 0, 0, 0, home_lat, home_lon, home_alt])]

    def add(item):
        params = [0 if value is None else value for value in item["params"]]
        items.append((item["frame"], item["command"], item.get("autoContinue", True), params))

    for item in mission["items"]:
        if item["type"] == "SimpleItem":
            add(item)
        elif "TransectStyleComplexItem" in item:   # survey or corridor scan drawn in QGroundControl
            for inner in item["TransectStyleComplexItem"]["Items"]:
                add(inner)
        else:
            raise ValueError(f"unsupported item in the plan: {item.get('complexItemType', item['type'])}")
    return items


def send_item(link, seq, item):
    """Send one mission item. Latitude and longitude go as whole numbers (degrees x 10^7)."""
    frame, command, auto_continue, (p1, p2, p3, p4, lat, lon, alt) = item
    link.mav.mission_item_int_send(link.target_system, link.target_component, seq, frame, command,
                                   0, int(auto_continue), p1, p2, p3, p4,
                                   int(round(lat * 1e7)), int(round(lon * 1e7)), alt)


def upload_mission(link, path):
    """
    Send the mission to the flight controller, item by item, as it asks for them.

    Announcing the number of items starts a new upload that replaces the old mission.
    The upload only counts as done when the drone has asked for every item and then
    confirms; an earlier, unrelated confirmation is ignored.
    """
    items = load_plan(path)
    count = len(items)
    link.waypoint_count_send(count)
    sent = set()
    while True:
        message = link.recv_match(type=["MISSION_REQUEST", "MISSION_REQUEST_INT", "MISSION_ACK"],
                                  blocking=True, timeout=10)
        if message is None:
            raise RuntimeError("the flight controller stopped asking for mission items")
        if message.get_type() == "MISSION_ACK":
            if len(sent) < count:
                continue   # not the confirmation for this upload
            if message.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
                raise RuntimeError(f"mission rejected (code {message.type})")
            return count
        send_item(link, message.seq, items[message.seq])
        sent.add(message.seq)


def stored_mission_count(link):
    """Ask the flight controller how many mission items it has stored."""
    link.waypoint_request_list_send()
    reply = link.recv_match(type="MISSION_COUNT", blocking=True, timeout=5)
    return reply.count if reply else None


def upload_with_retries(link, path, attempts=5):
    """
    Upload the mission and check that the drone really stored it. Right after the
    simulator starts it can drop out of the upload, so a failed attempt is repeated.
    """
    for attempt in range(1, attempts + 1):
        try:
            count = upload_mission(link, path)
            if stored_mission_count(link) == count:
                return count
            log(f"upload attempt {attempt}: the drone did not store all items")
        except RuntimeError as error:
            log(f"upload attempt {attempt} failed: {error}")
        time.sleep(5)
    raise RuntimeError(f"mission upload failed after {attempts} attempts")


def wait_until_ready(link, timeout_s=180):
    """
    Wait until the drone reports that its pre-arm checks pass (sensors settled, GPS fix,
    position estimate). Arming earlier only fills the ground station with error messages.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = link.recv_match(type="SYS_STATUS", blocking=True, timeout=5)
        if status and status.onboard_control_sensors_health & mavutil.mavlink.MAV_SYS_STATUS_PREARM_CHECK:
            return
    log("pre-arm checks still not reported as passed; trying to arm anyway")


def arm_in_auto(link):
    """Switch to AUTO and arm. If the drone still refuses, try again a few seconds later."""
    while True:
        link.set_mode("AUTO")
        link.arducopter_arm()
        ack = link.recv_match(type="COMMAND_ACK", blocking=True, timeout=3)
        if ack and ack.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM \
                and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            return
        time.sleep(5)


def drone_time_s(link):
    """The drone's own clock in seconds since it started."""
    message = link.recv_match(type="SYSTEM_TIME", blocking=True, timeout=5)
    return message.time_boot_ms / 1000


def main():
    path = sys.argv[1]   # the flight plan, e.g. /missions/flight.plan

    # 1. Connect to the simulated flight controller (waits until the simulator is up).
    link = connect()
    log(f"connected, uploading {path}")

    # 2. Prepare the drone: ask for the status messages this script needs, and allow
    #    arming and taking off in AUTO mode without a pilot.
    request_messages(link)
    set_parameter(link, "AUTO_OPTIONS", AUTO_OPTIONS)

    # 3. Upload the flight plan and make sure the drone stored all of it.
    count = upload_with_retries(link, path)
    log(f"mission uploaded and stored ({count} items), waiting until the drone is ready to fly")

    # 4. Wait for GPS and the position estimate, then start the mission.
    #    The start time is taken from the drone's clock, to measure the flight time later.
    wait_until_ready(link)
    arm_in_auto(link)
    start = drone_time_s(link)
    log("armed in AUTO, mission started")

    # 5. Follow the flight: log each new mission item the drone flies to, and stop
    #    watching once the drone has landed (after landing it disarms its motors).
    current_item = -1
    while True:
        message = link.recv_match(type=["MISSION_CURRENT", "HEARTBEAT"], blocking=True, timeout=5)
        if message is None:
            continue

        # MISSION_CURRENT: the item the drone is flying to right now.
        if message.get_type() == "MISSION_CURRENT" and message.seq != current_item:
            current_item = message.seq
            log(f"flying to item {current_item} of {count - 1}")

        # HEARTBEAT from the drone without the "armed" flag: it has landed and disarmed.
        if message.get_type() == "HEARTBEAT" and message.get_srcSystem() == link.target_system \
                and not message.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
            break

    # 6. Report how long the flight took, from arming to landing (minutes:seconds).
    duration = drone_time_s(link) - start
    log(f"landed; flight took {int(duration) // 60}:{int(duration) % 60:02d} ({duration:.0f} s)")


if __name__ == "__main__":
    main()
