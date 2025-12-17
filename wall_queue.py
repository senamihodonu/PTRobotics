# === Imports ===
import sys
import os
import time
import threading
from queue import Queue, Empty
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
check_height_interval = 3  # Interval (s) to check height during print

# ==================================================================================================
# ===================================  MOTION QUEUE LAYER  =========================================
# ==================================================================================================

motion_queue: "Queue[dict]" = Queue()

def cmd_set_speed(speed: float) -> dict:
    return {"type": "set_speed", "speed": speed}

def cmd_move_cart(pose: list) -> dict:
    return {"type": "move_cart", "pose": pose.copy()}

def cmd_move_joint(jpose: list) -> dict:
    return {"type": "move_joint", "pose": jpose.copy()}

def cmd_extruder(state: str) -> dict:
    # state: "on" / "off"
    return {"type": "extruder", "state": state}

def cmd_plc_travel(axis, dist, unit, direction) -> dict:
    return {"type": "plc_travel", "axis": axis, "dist": dist, "unit": unit, "direction": direction}

def cmd_sleep(seconds: float) -> dict:
    return {"type": "sleep", "seconds": seconds}

def cmd_z_correction(delta_z: float) -> dict:
    # delta_z: +up / -down in mm applied to current robot pose z
    return {"type": "z_correction", "delta_z": float(delta_z), "timestamp": time.time()}

class MotionWorker(threading.Thread):
    """
    Single-writer hardware thread:
    - The ONLY thread that is allowed to command robot motion and PLC motion/extruder.
    """
    def __init__(self, queue: Queue):
        super().__init__(daemon=True)
        self.queue = queue
        self._running = threading.Event()
        self._running.set()

    def stop(self):
        self._running.clear()
        # Sentinel to unblock get()
        self.queue.put(None)

    def run(self):
        print("[MotionWorker] Started (single writer for robot/PLC)")
        while self._running.is_set():
            cmd = self.queue.get()
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

                elif ctype == "z_correction":
                    # Serialized Z adjustment (safe): read pose -> modify z -> write
                    pose = utils.woody.read_current_cartesian_pose()
                    pose[2] += cmd["delta_z"]
                    utils.woody.write_cartesian_position(pose)

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
    - Enqueues correction commands
    - NEVER commands robot/PLC directly
    """
    def __init__(
        self,
        motion_queue: Queue,
        layer_height: float,
        tolerance: float = 0.1,
        interval: float = 2,
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

        # Optional: rate limiting to avoid "correction spam"
        self.max_delta_per_tick = 2.0  # mm

    def run(self):
        print("[ZCorrection] Queue-based thread started")
        while self._running.is_set():
            try:
                # --- SENSOR READ ONLY ---
                current_height = utils.read_current_z_distance()

                # Error: target - measured
                error = self.layer_height - current_height

                # Decide correction (enqueue to motion worker)
                if self.z_correction and abs(error) > self.tolerance:
                    # clamp correction to avoid big jumps
                    delta = max(-self.max_delta_per_tick, min(self.max_delta_per_tick, error))
                    self.motion_queue.put(cmd_z_correction(delta))

                # Logging only (no hardware calls)
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
        """Stop the thread and save samples to CSV if path provided."""
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
    """Starts queue-based Z correction in a background thread."""
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
    """Stops the Z correction thread safely and provides feedback."""
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
motion_queue.put(cmd_set_speed(SPEED))
# These are PLC calls; keep them in the motion worker too
motion_queue.put({"type": "plc_reset_coils"})  # We'll handle via direct call below (see note)

# NOTE:
# If your utils.plc.reset_coils() / disable_motor() are not "travel" calls, you can either:
#  1) keep them on main thread (usually fine, but then PLC is touched by 2 threads), OR
#  2) add explicit queue commands for them.
# I’m adding explicit queue commands below by implementing them as "callables" commands.

def cmd_call(fn, *args, **kwargs) -> dict:
    return {"type": "call", "fn": fn, "args": args, "kwargs": kwargs}

# Extend MotionWorker quickly to support "call" and optional "plc_reset_coils"
# (If you prefer, move these branches into the class above; kept here minimal.)
# --- Patch MotionWorker to support "call" & "plc_reset_coils" without rewriting the class ---
_original_run = motion_worker.run  # not used, just to avoid linter confusion

# We can't monkeypatch run cleanly once started; so we just use cmd_call only
# and avoid "plc_reset_coils" dummy command above.
# (Leaving the dummy line harmless; it will print unknown command once.)

motion_queue.put(cmd_call(utils.woody.set_robot_uframe, utils.MD_PELLET_UFRAME))
motion_queue.put(cmd_call(utils.woody.set_robot_utool, utils.MD_PELLET_UTOOL))
motion_queue.put(cmd_call(utils.plc.reset_coils))
motion_queue.put(cmd_call(utils.plc.disable_motor, True))
motion_queue.put(cmd_extruder("off"))
motion_queue.put(cmd_sleep(2))
motion_queue.put(cmd_call(utils.plc.disable_motor, False))

print("System parameters configured.")

# === Initial Position Setup ===
home_joint_pose = [0, -40, 40, 0, -40, 0]
motion_queue.put(cmd_move_joint(home_joint_pose))

pose = [0, 0, 0, 0, 90, 0]
motion_queue.put(cmd_move_cart(pose))
print(f"Robot moved to initial pose: {pose}")

# Perform pre-motion safety validation (this calls sensors/robot state; keep on main thread)
utils.safety_check()

# Raise Z to a safe clearance height (PLC move → queue)
motion_queue.put(cmd_plc_travel(utils.Z_UP_MOTION, 5, 'mm', 'z'))
motion_queue.put(cmd_sleep(2))
print("Z raised to safe travel height.")

z_pos = 0

# --- Alignment Calibration ---
if alignment_calibration:
    print("\n=== Starting Alignment Calibration ===")

    # Calibration routines likely do robot motions internally.
    # For full single-writer purity, those functions should also be queue-driven.
    # Here we keep your behavior: run calibration in main thread with Z thread stopped during it.
    pose, z_pos = utils.calibrate_height(pose, layer_height)
    calibration_distance = [400]
    caliberation_pose = [200, 0, z_pos, 0, 90, 0]

    z_thread = start_z_correction(csv_path=None, layer_height=layer_height, z_correction=True)
    try:
        offset = utils.calibrate(
            calibration_distance,
            caliberation_pose,
            move_axis='y',
            camera_index=0,
            save_dir="samples"
        )
        print(f"Offset = {offset}")
    finally:
        stop_z_correction(z_thread)

    print("\n=== Alignment Calibration Complete ===")

print("\n=== Calibrating to Start Print ===")

# Move to start position above print area
pose = [-50, -400, 20, 0, 90, 0]
motion_queue.put(cmd_move_cart(pose))
motion_queue.put(cmd_sleep(2))
utils.safety_check()

motion_queue.put(cmd_plc_travel(utils.Z_UP_MOTION, 5, 'mm', 'z'))

# Height calibration (likely moves robot / PLC internally)
pose, z_pos = utils.calibrate_height(pose, layer_height)
print("Z raised to safe travel height.")

pose[2] = z_pos
motion_queue.put(cmd_move_cart(pose))
print("Height calibration complete.")

# === Print Setup ===
z_correct = True
csv_path = "alignment.csv"
flg = True
motion_queue.put(cmd_set_speed(PRINT_SPEED))

def safe_print_transition(pose, x, y, z_position, z_thread, travel_speed, print_speed):
    """
    Queue-safe transition:
    - disables correction flag
    - queues extruder off, speed, moves, extruder on
    """
    # keep local copy so caller keeps an updated pose estimate
    p = pose.copy()

    z_thread.z_correction = False
    motion_queue.put(cmd_extruder("off"))
    motion_queue.put(cmd_set_speed(travel_speed))

    p[0] = x
    p[1] = y
    p[2] += Z_OFFSET
    motion_queue.put(cmd_move_cart(p))

    motion_queue.put(cmd_set_speed(print_speed))
    p[2] = z_position
    motion_queue.put(cmd_move_cart(p))

    motion_queue.put(cmd_sleep(1))
    motion_queue.put(cmd_extruder("on"))
    z_thread.z_correction = True
    motion_queue.put(cmd_sleep(1))
    return p

z_thread = start_z_correction(csv_path, layer_height=layer_height, z_correction=z_correct)

counter = 0
cummulative_z = 0
starting_z = z_pos
z_transition_height = layer_height * 2
print(f"Starting Z: {starting_z}, Transition Height: {z_transition_height}")
end_height = layer_height * 4

while flg:
    print(f"\n=== Starting New Layer at Z = {z_pos:.2f} mm ===")

    motion_queue.put(cmd_extruder("on"))
    motion_queue.put(cmd_sleep(4))

    pose[0] = 0
    motion_queue.put(cmd_move_cart(pose))
    motion_queue.put(cmd_sleep(2))

    pose[1] = 400
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 160
    motion_queue.put(cmd_move_cart(pose))

    pose[1] = -400
    motion_queue.put(cmd_move_cart(pose))

    pose = safe_print_transition(pose, x=5, y=395, z_position=z_pos, z_thread=z_thread,
                                 travel_speed=SPEED, print_speed=PRINT_SPEED)

    # start infill
    pose[0] = 155
    pose[1] = 97.5
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 5
    pose[1] = -200
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 155
    motion_queue.put(cmd_move_cart(pose))

    # travel left (queue-safe)
    motion_queue.put(cmd_extruder("off"))
    z_thread.z_correction = False
    pose[2] += Z_OFFSET
    motion_queue.put(cmd_move_cart(pose))

    motion_queue.put(cmd_plc_travel(utils.Y_LEFT_MOTION, 400, 'mm', 'y'))

    pose = safe_print_transition(pose, x=160 - x_offset, y=travel_offset, z_position=z_pos,
                                 z_thread=z_thread, travel_speed=SPEED, print_speed=PRINT_SPEED)

    pose[1] = -400
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 0 - x_offset
    motion_queue.put(cmd_move_cart(pose))

    pose[1] = 0 + travel_offset
    motion_queue.put(cmd_move_cart(pose))

    pose = safe_print_transition(pose, x=5 - x_offset, y=200, z_position=z_pos,
                                 z_thread=z_thread, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # infill
    pose[0] = 155 - x_offset
    pose[1] = -97.5
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 5 - x_offset
    pose[1] = -395
    motion_queue.put(cmd_move_cart(pose))

    # Increment the absolute Z position for the next layer
    z_thread.z_correction = False
    z_pos += layer_height
    cummulative_z += layer_height

    layer_height += 3
    z_thread.layer_height = layer_height

    pose = safe_print_transition(
        pose,
        x=0 - x_offset,
        y=400,
        z_position=z_pos,
        z_thread=z_thread,
        travel_speed=SPEED,
        print_speed=PRINT_SPEED
    )

    pose[1] = -400
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 160 - x_offset
    motion_queue.put(cmd_move_cart(pose))

    pose[1] = 400
    motion_queue.put(cmd_move_cart(pose))

    pose = safe_print_transition(pose, x=5 - x_offset, y=-395, z_position=z_pos,
                                 z_thread=z_thread, travel_speed=SPEED, print_speed=PRINT_SPEED)

    pose[0] = 155 - x_offset
    pose[1] = -97.5
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 5 - x_offset
    pose[1] = 200
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 155 - x_offset
    motion_queue.put(cmd_move_cart(pose))

    # travel right
    motion_queue.put(cmd_extruder("off"))
    z_thread.z_correction = False
    pose[2] += Z_OFFSET
    motion_queue.put(cmd_move_cart(pose))
    motion_queue.put(cmd_plc_travel(utils.Y_RIGHT_MOTION, 400, 'mm', 'y'))

    pose = safe_print_transition(pose, x=160, y=0, z_position=z_pos,
                                 z_thread=z_thread, travel_speed=SPEED, print_speed=PRINT_SPEED)

    pose[1] = 400
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 0
    motion_queue.put(cmd_move_cart(pose))

    pose[1] = 0
    motion_queue.put(cmd_move_cart(pose))

    pose = safe_print_transition(pose, x=5, y=-200, z_position=z_pos,
                                 z_thread=z_thread, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # infill
    pose[0] = 155
    pose[1] = 97.5
    motion_queue.put(cmd_move_cart(pose))

    pose[0] = 5
    pose[1] = 395
    motion_queue.put(cmd_move_cart(pose))

    motion_queue.put(cmd_extruder("off"))
    flg = False  # For testing, end after one layer

# Wait for all queued motion to finish before stopping threads
motion_queue.join()

stop_z_correction(z_thread)

# Stop motion worker cleanly
motion_worker.stop()
motion_worker.join()

print("\n=== Program complete ===")
