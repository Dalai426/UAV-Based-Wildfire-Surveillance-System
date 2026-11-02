import asyncio
import os
import time
from datetime import datetime, timezone

from mavsdk.asyncio import ComponentType, Configuration, Mavsdk
from mavsdk.asyncio.plugins.telemetry import TelemetryAsync, TelemetryError


# Where the Core listens for the drone's MAVLink telemetry.
#
# "udpin://0.0.0.0:14551" = listen on UDP port 14551 on every
# network interface of this container. compose.yml publishes
# this port on the host, so the drone can send to it.
TELEMETRY_CONNECTION_URL = os.environ.get(
    "TELEMETRY_CONNECTION_URL",
    "udpin://0.0.0.0:14551",
)

# No position update for this long -> the link counts as STALE.
STALE_AFTER_S = 2.0

# How often we ask the autopilot to send position, velocity
# and attitude (updates per second).
TELEMETRY_RATE_HZ = 10.0

# How long to wait before reconnecting after the telemetry
# receiver failed.
RETRY_AFTER_S = 5.0


class TelemetryState:
    """
    The latest telemetry received from the drone.

    The telemetry receiver writes into it, the API reads from it.

    Both run in the same asyncio event loop (FastAPI's), so they
    never run at the same moment and no lock is needed.
    """

    def __init__(self):
        self._data = {
            # Where
            "lat": None,
            "lon": None,
            "alt_rel_home_m": None,
            "alt_amsl_m": None,
            "heading_deg": None,

            # How it moves and how it is tilted
            "vel_north_m_s": None,
            "vel_east_m_s": None,
            "vel_down_m_s": None,
            "roll_deg": None,
            "pitch_deg": None,
            "yaw_deg": None,

            # The autopilot's own clock (seconds since it started)
            # for the latest attitude message.
            "drone_time_s": None,

            # Drone state
            "battery_pct": None,
            "battery_v": None,
            "flight_mode": None,
            "armed": None,
        }

        # When the last position arrived (time.time()).
        # A position update is how the drone counts as "alive".
        self._last_position_time = None

        # Before its GPS is ready, the simulator sends 0,0 as
        # its position. That is not a real position yet.
        self._has_fix = False

        # Set when the telemetry receiver failed, cleared when
        # it reconnects.
        self.error = None

    def update(self, **fields):
        """
        Store new values, e.g. update(lat=55.76, lon=12.38).
        """

        self._data.update(fields)

        if "lat" in fields:
            self._last_position_time = time.time()
            self._has_fix = not (
                fields["lat"] == 0 and fields["lon"] == 0
            )

    def link_status(self):
        """
        How healthy the telemetry link is right now.

        ERROR    the telemetry receiver failed
        NO LINK  no position has ever arrived
        STALE    the last position is older than STALE_AFTER_S
        NO FIX   positions arrive, but the GPS is not ready yet
        OK       everything is fine
        """

        if self.error is not None:
            return "ERROR"

        if self._last_position_time is None:
            return "NO LINK"

        if time.time() - self._last_position_time > STALE_AFTER_S:
            return "STALE"

        if not self._has_fix:
            return "NO FIX"

        return "OK"

    def snapshot(self):
        """
        Return a copy of all fields, plus the link status,
        the ground speed and when the last position arrived.
        """

        data = dict(self._data)

        data["link_status"] = self.link_status()

        # Ground speed from the north and east velocity,
        # using Pythagoras.
        north = data["vel_north_m_s"]
        east = data["vel_east_m_s"]

        if north is not None and east is not None:
            data["ground_speed_m_s"] = (north ** 2 + east ** 2) ** 0.5
        else:
            data["ground_speed_m_s"] = None

        if self._last_position_time is not None:
            data["last_position_utc"] = datetime.fromtimestamp(
                self._last_position_time,
                timezone.utc,
            ).isoformat()
        else:
            data["last_position_utc"] = None

        return data


async def receive_telemetry(state: TelemetryState, connection_url: str):
    """
    Connect to the drone's autopilot and copy every telemetry
    update into `state`, until the connection fails.
    """

    # We identify ourselves to the drone as a ground station.
    config = Configuration.create_with_component_type(
        ComponentType.GROUND_STATION
    )

    # "async with" shuts MAVSDK down cleanly when the block ends,
    # also when it ends with an error.
    async with Mavsdk(config) as mavsdk:

        await mavsdk.add_any_connection(connection_url)
        print(f"Telemetry: waiting for the drone on {connection_url}")

        # Wait until an autopilot sends its heartbeat.
        # This way the Core can start before the drone.
        system = None
        while system is None:
            system = await mavsdk.first_autopilot(timeout_s=5.0)

        print("Telemetry: connected to the drone")
        state.error = None

        telemetry = TelemetryAsync(system)

        async def request_rates():
            # Ask the autopilot for 10 updates per second.
            # Runs next to the subscriptions below, so a slow or
            # unanswered request never delays the data.
            for set_rate in (
                telemetry.set_rate_position,
                telemetry.set_rate_velocity_ned,
                telemetry.set_rate_attitude_euler,
            ):
                try:
                    await set_rate(TELEMETRY_RATE_HZ)
                except TelemetryError as exc:
                    print(
                        f"Telemetry: could not set the rate ({exc}); "
                        "using the autopilot's default"
                    )

        # One small loop per kind of telemetry. Each waits for
        # new values and stores them.

        async def position():
            async for p in telemetry.subscribe_position():
                state.update(
                    lat=p.latitude_deg,
                    lon=p.longitude_deg,
                    alt_rel_home_m=p.relative_altitude_m,
                    alt_amsl_m=p.absolute_altitude_m,
                )

        async def heading():
            async for h in telemetry.subscribe_heading():
                state.update(heading_deg=h.heading_deg)

        async def attitude():
            # timestamp_us is the autopilot's own clock: when the
            # drone measured this attitude.
            async for a in telemetry.subscribe_attitude_euler():
                state.update(
                    roll_deg=a.roll_deg,
                    pitch_deg=a.pitch_deg,
                    yaw_deg=a.yaw_deg,
                    drone_time_s=a.timestamp_us / 1e6,
                )

        async def velocity():
            async for v in telemetry.subscribe_velocity_ned():
                state.update(
                    vel_north_m_s=v.north_m_s,
                    vel_east_m_s=v.east_m_s,
                    vel_down_m_s=v.down_m_s,
                )

        async def battery():
            async for b in telemetry.subscribe_battery():
                state.update(
                    battery_pct=b.remaining_percent,
                    battery_v=b.voltage_v,
                )

        async def flight_mode():
            async for mode in telemetry.subscribe_flight_mode():
                state.update(flight_mode=mode.name)

        async def armed():
            async for is_armed in telemetry.subscribe_armed():
                state.update(armed=is_armed)

        # Run all loops at the same time, until one of them fails.
        await asyncio.gather(
            request_rates(),
            position(),
            heading(),
            attitude(),
            velocity(),
            battery(),
            flight_mode(),
            armed(),
        )


async def run_telemetry_forever(state: TelemetryState):
    """
    Keep the telemetry receiver running for as long as the Core runs.

    If it fails, remember the error (the link shows as ERROR),
    wait a moment and connect again.
    """

    while True:
        try:
            await receive_telemetry(state, TELEMETRY_CONNECTION_URL)

        except asyncio.CancelledError:
            # The Core is shutting down: stop quietly.
            raise

        except Exception as exc:
            state.error = exc
            print(
                f"Telemetry: receiver failed ({exc!r}); "
                f"retrying in {RETRY_AFTER_S:.0f} s"
            )

        await asyncio.sleep(RETRY_AFTER_S)
