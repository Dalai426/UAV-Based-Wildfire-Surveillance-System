from pymavlink import mavutil
import time
import os
import signal
import subprocess
import sys

CONNECTION = "tcp:sitl:5763"

def connect():
    """Connect to the flight controller, waiting until the simulator is up."""
    while True:
        try:
            link = mavutil.mavlink_connection(CONNECTION, source_system=251, autoreconnect=True)
            if link.wait_heartbeat(timeout=10):
                return link
        except OSError:
            pass   # simulator not started yet
        time.sleep(2)

def start_stream():
    """Start stream_video.sh with the arguments from compose.yml."""
    stream = subprocess.Popen(["stream_video.sh", *sys.argv[1:]], start_new_session=True)
    print("camera: video stream has started", flush=True)
    return stream


def stop_stream(stream):
    """Stop stream_video.sh and the ffmpeg it started."""
    # stop bash, ffmpeg and awk together
    os.killpg(stream.pid, signal.SIGTERM)
    # wait until they have actually exited
    stream.wait()
    print("camera: video stream stopped", flush=True)

def main():
    link = connect()
    print("camera: connected to the flight controller", flush=True)

    # the running stream_video.sh, or None
    stream = None
    
    # Runs forever: each round handles one heartbeat (the drone sends one per second)
    while True:
        # Wait up to 3s for the next HEARTBEAT
        try:
            msg = link.recv_match(type="HEARTBEAT", blocking=True, timeout=3)
        except OSError:
            # sitl is gone and pymavlink's own reconnect attempts failed:
            # stop the video, then wait in connect() until sitl is back
            print("camera: lost the flight controller, reconnecting", flush=True)
            if stream is not None and stream.poll() is None:
                stop_stream(stream)
            stream = None
            link = connect()
            print("camera: reconnected to the flight controller", flush=True)
            continue

        # None: nothing for 3s, sitl stopped; restart loop
        if msg is None:
            print("camera: no heartbeat", flush=True)
            if stream is not None and stream.poll() is None: 
                stop_stream(stream)
            stream = None
            continue

        # Skip heartbeats from other programs (MAVProxy, fly_mission.py);
        # component 1 is the flight controller
        if msg.get_srcComponent() != 1:
            continue
        
        # base_mode holds on/off flags & keeps only the "armed" flag
        armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)

        if not armed:
            if stream is not None and stream.poll() is None: 
                stop_stream(stream)
            stream = None
        else:
            if stream is None:
                stream = start_stream()
            if stream.poll() is not None and stream.poll() != 0:
                time.sleep(2)
                stream = start_stream()


if __name__ == "__main__":
    main()