# === Imports ===
import sys
import os
import time
import threading
from queue import PriorityQueue
import pandas as pd

import utils  # custom utility module

# === Parameters ===
alignment_calibration = False  # Flag to enable alignment calibration
SPEED = 100             # Robot travel speed (mm/s)
PRINT_SPEED = 12        # Printing speed (mm/s)
INSIDE_OFFSET = 6       # Offset for inner infill moves (mm)
layer_height = 3        # Vertical step per layer (mm)
Z_OFFSET = 20           # Safe Z offset for travel moves (mm)
x_offset = 10           # X-axis offset (mm)
PRINT_OFFSET = 5        # Vertical offset between passes (mm)
Z_CORRECTION = 4        # Small Z alignment correction (mm)
TOL = 0                 # Tolerance for Z correction
travel_offset = 6
check_height_interval = 0.5  # ✅ faster loop for “real-time” feel

# ==================================================================================================
# ===================================  PRIORITY MOTION QUEUE  ======================================
# ==================================================================================================

# Lower number = higher priority
PRIO_Z = 1
PRIO_MOVE = 5
PRIO_STOP = 99

motion_queue: "PriorityQueue[tuple[int, float, dict|None]]" = PriorityQueue()

def put_cmd(cmd: dict, prio: int = PRIO_MOVE):
    """Enqueue a command with priority."""
    motion_queue.put((prio, time.time(), cmd))

# === Command builders ===
def cmd_set_speed(speed: float) -> dict:
    return {"type": "set_speed", "speed": speed}

def cmd_move_cart(pose: list) -> dict:
    return {"type": "move_cart", "pose": pose.copy()}

def cmd_move_joint(jpose: list) -> dict:
    return {"type": "move_joint", "pose": jpose.copy()}

def cmd_extruder(state: str) -> dict:
    return {"type": "extruder", "state": state}

def cmd_plc_travel(axis, dist, unit, direction) -> dict:
    return {"type": "plc_travel", "axis": axis, "dist": dist, "unit": unit, "direction": direction}

def cmd_sleep(seconds: float) -> dict:
    return {"type": "sleep", "seconds": seconds}

def cmd_call(fn, *args, **kwargs) -> dict:
    return {"type": "call", "fn": fn, "args": args, "kwargs": kwargs}

def cmd_z_correction(delta_z: float) -> dict:
    # delta_z: +up / -down in mm (GANTRY Z in your case)
    return {"type": "z_correction", "delta_z": float(delta_z), "timestamp": time.time()}

class MotionWorker(threading.Thread):
    """
    Single-writer hardware thread:
    - The ONLY thread that is allowed to command robot motion and PLC motion/extruder.
    """
    def __init__(self, queue: PriorityQueue):
        super().__init__(daemon=True)
        self.queue = queue
        self._running = threading.Event()
        self._running.set()

    def stop(self):
        self._running.clear()
        # Sentinel to unblock get()
        self.queue.put((PRIO_STOP, time.time(), None))

    def run(self):
        print("[MotionWorker] Started (single writer for robot/PLC)")
        while self._running.is_set():
            prio, ts, cmd = self.queue.get()
            try:
                if cmd is None:
                    break

                ctype = cmd.get("type")

                if ctype == "set_speed":
                    utils.woody.set_speed(cmd["speed"])

                elif ctype == "move_cart":
                    utils.woody.write_cartesian_position(cmd["pose"])

                elif ctype == "move_joint":
                    utils.woody.write_joint_pose(cmd["pose"])

                elif ctype == "extruder":
                    utils.plc.md_extruder_switch(cmd["state"])

                elif ctype == "plc_travel":
                    utils.plc.travel(cmd["axis"], cmd["dist"], cmd["unit"], cmd["direction"])

                elif ctype == "sleep":
                    time.sleep(cmd["seconds"])

                elif ctype == "call":
                    fn = cmd["fn"]
                    args = cmd.get("args", ())
                    kwargs = cmd.get("kwargs", {})
                    fn(*args, **kwargs)

                elif ctype == "z_correction":
                    # ✅ GANTRY Z correction via PLC, serialized and prioritized
                    delta = cmd["delta_z"]
                    direction = utils.Z_UP_MOTION if delta > 0 else utils.Z_DOWN_MOTION
                    distance = abs(delta)

                    print(f"[MotionWorker] GANTRY Z correction Δ={delta:.3f} mm")
                    utils.plc.travel(direction, distance, 'mm', 'z')

                else:
                    print(f"[MotionWorker] Unknown command: {cmd}")

            except Exception as e:
                print(f"[MotionWorker] Error executing {cmd}: {e}")
            finally:
                self.queue.task_done()

# Start motion worker immediately so even setup moves are serialized
motion_worker = MotionWorker(motion_queue)
motion_worker.start()

# ==================================================================================================
# =================================  QUEUE-BASED Z CORRECTION  =====================================
# ==================================================================================================

class ZCorrectionThread(threading.Thread):
    """
    Queue-based Z correction:
    - Reads sensors / computes delta
    - Enqueues correction commands (HIGH PRIORITY)
    - NEVER commands robot/PLC directly
    """
    def __init__(
        self,
        motion_queue: PriorityQueue,
        layer_height: float,
        tolerance: float = 0.1,
        interval: float = 0.5,
        csv_path: str | None = None,
        z_correction: bool = False
    ):
        super().__init__(daemon=True)
        self.motion_queue = motion_queue
        self.layer_height = layer_height
        self.tolerance = tolerance
        self.interval = interval
        self.csv_path = csv_path
        self._running = threading.Event()
        self._running.set()
        self.samples = []
        self.z_correction = z_correction

        # Rate limiting
        self.max_delta_per_tick = 1.0  # ✅ keep small for smoother real-time corrections

    def run(self):
        print("[ZCorrection] Queue-based thread started")
        while self._running.is_set():
            try:
                current_height = utils.read_current_z_distance()
                error = self.layer_height - current_height

                # Debug visibility (helps you confirm it’s alive)
                # print(f"[ZCorrection] h={current_height:.2f} target={self.layer_height:.2f} err={error:.2f} enabled={self.z_correction}")

                if self.z_correction and abs(error) > self.tolerance:
                    delta = max(-self.max_delta_per_tick, min(self.max_delta_per_tick, error))
                    # ✅ HIGH PRIORITY so it happens during printing, not after the layer
                    self.motion_queue.put((PRIO_Z, time.time(), cmd_z_correction(delta)))

                self.samples.append({
                    "current_height": current_height,
                    "layer_height": self.layer_height,
                    "error": error,
                    "z_correction_enabled": self.z_correction,
                    "timestamp": time.time()
                })

            except Exception as e:
                print(f"[ZCorrection] Error: {e}")

            time.sleep(self.interval)

    def stop(self):
        print("[ZCorrection] Thread stopping...")
        self._running.clear()

        if self.csv_path and self.samples:
            try:
                df = pd.DataFrame(self.samples)
                file_exists = os.path.isfile(self.csv_path)
                df.to_csv(self.csv_path, mode='a', index=False, header=not file_exists)
                print(f"[ZCorrection] Appended {len(df)} samples to {self.csv_path}")
            except Exception as e:
                print(f"[ZCorrection] Error appending CSV: {e}")

# === Helper Functions ===
def start_z_correction(csv_path, layer_height=layer_height, z_correction=False):
    z_thread = ZCorrectionThread(
        motion_queue=motion_queue,
        layer_height=layer_height,
        tolerance=1,
        interval=check_height_interval,
        csv_path=csv_path,
        z_correction=z_correction
    )
    z_thread.start()
    print("✅ Queue-based Z correction thread started.")
    return z_thread

def stop_z_correction(z_thread: ZCorrectionThread | None):
    if z_thread is None:
        print("⚠️  No Z correction thread to stop.")
        return

    if z_thread.is_alive():
        print("🟡 Stopping Z correction thread...")
        z_thread.stop()
        z_thread.join()
        print("✅ Z correction thread stopped successfully.")
    else:
        print("ℹ️  Z correction thread is not running.")

# ==================================================================================================
# ========================================  PROGRAM  ===============================================
# ==================================================================================================

print("=== Program initialized ===")

# === Robot & PLC Setup ===
utils.woody.set_robot_uframe(utils.MD_PELLET_UFRAME)     # Select pellet extruder user frame
utils.woody.set_robot_utool(utils.MD_PELLET_UTOOL)       # Select pellet extruder tool frame
utils.woody.set_speed(SPEED)                             # Set travel speed (mm/s)

# Reset PLC output states
utils.plc.reset_coils()
utils.plc.disable_motor(True)
utils.plc.md_extruder_switch("off")
time.sleep(2)
utils.plc.disable_motor(False)


print("System parameters configured.")

# === Initial Position Setup ===
home_joint_pose = [0, -40, 40, 0, -40, 0]
utils.woody.write_joint_pose(home_joint_pose)

pose = [-50, -400, 20, 0, 90, 0]
utils.woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")


# Pre-motion safety validation
utils.safety_check()

# Raise Z to a safe clearance height
utils.plc.travel(utils.Z_UP_MOTION, 10, 'mm', 'z')
time.sleep(2)
print("Z raised to safe travel height.")

z_pos = 0

print("\n=== Calibrating to Start Print ===")


# Height calibration (may move robot/PLC internally)
pose, z_pos = utils.calibrate_height(pose, layer_height)
pose[2] = z_pos
utils.woody.write_cartesian_position(pose)
print("Height calibration complete.")

# === Print Setup ===
z_correct = True
csv_path = "alignment.csv"
flg = True
put_cmd(cmd_set_speed(PRINT_SPEED))

def safe_print_transition(pose, x, y, z_position, z_thread, travel_speed, print_speed):
    p = pose.copy()

    z_thread.z_correction = False
    put_cmd(cmd_extruder("off"))
    put_cmd(cmd_set_speed(travel_speed))

    p[0] = x
    p[1] = y
    p[2] += Z_OFFSET
    put_cmd(cmd_move_cart(p))

    put_cmd(cmd_set_speed(print_speed))
    p[2] = z_position
    put_cmd(cmd_move_cart(p))

    put_cmd(cmd_sleep(1))
    put_cmd(cmd_extruder("on"))
    z_thread.z_correction = True
    put_cmd(cmd_sleep(1))
    return p

z_thread = start_z_correction(csv_path, layer_height=layer_height, z_correction=z_correct)

# ========================= MAIN PRINT LOOP (YOUR STRUCTURE) =========================
while flg:
    print(f"\n=== Starting New Layer at Z = {z_pos:.2f} mm ===")

    put_cmd(cmd_extruder("on"))
    put_cmd(cmd_sleep(4))

    pose[0] = 0
    put_cmd(cmd_move_cart(pose))
    put_cmd(cmd_sleep(2))

    pose[1] = 400
    put_cmd(cmd_move_cart(pose))

    pose[0] = 160
    put_cmd(cmd_move_cart(pose))

    pose[1] = -400
    put_cmd(cmd_move_cart(pose))

    pose = safe_print_transition(pose, x=5, y=395, z_position=z_pos, z_thread=z_thread,
                                 travel_speed=SPEED, print_speed=PRINT_SPEED)

    # infill
    pose[0] = 155
    pose[1] = 97.5
    put_cmd(cmd_move_cart(pose))

    pose[0] = 5
    pose[1] = -200
    put_cmd(cmd_move_cart(pose))

    pose[0] = 155
    put_cmd(cmd_move_cart(pose))

    # End after one layer (testing)
    put_cmd(cmd_extruder("off"))
    flg = False

# Wait for queued motion to finish
motion_queue.join()

stop_z_correction(z_thread)

motion_worker.stop()
motion_worker.join()

print("\n=== Program complete ===")
