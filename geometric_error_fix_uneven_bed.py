# === Imports ===
import sys
import os
import time
import threading
import pandas as pd

import utils  # custom utility module

print("=== Program initialized ===")

# === Parameters ===
SPEED = 200             # Robot travel speed (mm/s)
PRINT_SPEED = 10        # Printing speed (mm/s)
INSIDE_OFFSET = 6       # Offset for inner infill moves (mm)
LAYER_HEIGHT = 4        # Vertical step per layer (mm)
Z_OFFSET = 20           # Safe Z offset for travel moves (mm)
X_OFFSET = 9            # X-axis offset (mm)
PRINT_OFFSET = 5        # Vertical offset between passes (mm)
Z_CORRECTION = 4        # Small Z alignment correction (mm)
TOLERANCE = 0           # Tolerance for Z correction
Z_INCREMENT = LAYER_HEIGHT

print("Parameters set.")

# === Helper Functions ===
def apply_z_correction_brute(pose, layer_height, tolerance, extruding=False):
    """
    Apply Z correction safely.
    Turns extruder OFF during adjustment if needed.
    """
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        if extruding:
            utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)
        if extruding:
            utils.plc.md_extruder_switch("on")
    return pose


def apply_z_correction_gantry():
    """Placeholder for gantry-based Z correction."""
    pass


def safety_check():
    """
    Ensure no safety coils are active before starting.
    Moves Z down and Y right if any safety coil is active.
    """
    while any(utils.plc.read_modbus_coils(c) for c in (8, 9, 14)):
        print("Safety check: coils active, moving Z down and Y right...")
        for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
            utils.plc.write_modbus_coils(coil, True)

    # Turn off safety coils
    for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
        utils.plc.write_modbus_coils(coil, False)

    print("Safety check complete.")
    time.sleep(1)


def move_to_pose(pose, extruding=False, z_correct=False):
    """
    Move robot to a given pose with optional Z correction.
    """
    utils.woody.write_cartesian_position(pose)
    if z_correct:
        return apply_z_correction_brute(pose, LAYER_HEIGHT, TOLERANCE, extruding)
    return pose


def sweep_y_positions(pose, y_positions, extruding=False, z_correct=False):
    """
    Sweep through a list of Y positions at the current X coordinate.
    """
    for y in y_positions:
        pose[1] = y
        pose = move_to_pose(pose, extruding, z_correct)
    return pose


def lift_and_travel(pose, travel_distance, direction):
    """
    Lift Z by Z_OFFSET and travel in a given direction using PLC motion.
    """
    utils.plc.md_extruder_switch("off")
    utils.woody.set_speed(SPEED)

    pose[2] += Z_OFFSET
    utils.woody.write_cartesian_position(pose)

    utils.plc.travel(direction, travel_distance, 'mm', 'y')
    return pose


# === Machine Vision Mode ===
if len(sys.argv) > 1 and sys.argv[1].lower() in ("mv", "machinevision"):
    utils.open_all_cameras()
    print("Machine vision mode: cameras opened.")
else:
    print("Machine vision mode OFF (no cameras opened).")


# === Robot & PLC Setup ===
utils.woody.set_speed(SPEED)
utils.woody.set_robot_speed_percent(100)
utils.plc.reset_coils()
time.sleep(2)
print("Robot speed configured and PLC coils reset.")


# === Initial Pose ===
z = 0
pose = [-100, 0, z, 0, 90, 0]
utils.woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")


# === Safe Start & Safety Check ===
utils.plc.md_extruder_switch("off")
print("Extruder OFF for safe start.")
safety_check()
utils.plc.travel(utils.Z_UP_MOTION, 5, 'mm', 'z')


# === Height Calibration ===
pose, z = utils.calibrate_height(pose, LAYER_HEIGHT)
time.sleep(2)


# === Print Setup ===
utils.plc.md_extruder_switch("on")
print("Extruder ON, starting print sequence...")
time.sleep(4)


# === Z Correction Thread ===
class ZCorrectionThread(threading.Thread):
    def __init__(self, layer_height, tolerance=0.1, interval=3, csv_path=None, z_correction=False):
        super().__init__()
        self.layer_height = layer_height
        self.tolerance = tolerance
        self.interval = interval
        self.csv_path = csv_path
        self._running = threading.Event()
        self._running.set()
        self.samples = []
        self.z_correction = z_correction

    def run(self):
        print("[ZCorrection] Thread started")
        while self._running.is_set():
            try:
                if self.z_correction:
                    # Perform gantry Z correction
                    utils.apply_z_correction_gantry(self.layer_height, tolerance=self.tolerance)

                # Record current position and sensor height
                pose = utils.woody.read_current_cartesian_pose()
                x, y, z = pose[0], pose[1], pose[2]
                current_height = utils.read_current_z_distance()

                self.samples.append({
                    'x': x,
                    'y': y,
                    'z': z,
                    'current_height': current_height,
                    'timestamp': time.time()
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


# === Printing Loop (single-layer example) ===
flg = True
layer = 0
while flg:
    z_flag = False
    print(f"\n=== Starting new layer at z = {z:.2f} mm ===")

    pose = [-100, 0, z, 0, 90, 0]
    pose = move_to_pose(pose)

    # Start perimeter path
    utils.woody.set_speed(PRINT_SPEED)
    utils.plc.md_extruder_switch("on")
    time.sleep(3)
    print("Extruder ON for perimeter path.")

    # Start Z correction in background
    z_thread = ZCorrectionThread(LAYER_HEIGHT, tolerance=1, interval=2, csv_path="z_correction1.csv", z_correction=True)
    z_thread.start()

    # Example X/Y moves for perimeter
    pose[0] = -60; pose = move_to_pose(pose, extruding=True, z_correct=z_flag)
    pose[1] = 500; pose = move_to_pose(pose, extruding=True, z_correct=z_flag)

    pose[0] = 100; pose = move_to_pose(pose, extruding=True, z_correct=z_flag)
    pose[1] = -500; pose = move_to_pose(pose, extruding=True, z_correct=z_flag)

    pose[0] = -60; pose = move_to_pose(pose, extruding=True, z_correct=z_flag)
    pose[1] = 0; pose = move_to_pose(pose, extruding=True, z_correct=z_flag); time.sleep(1)

    utils.plc.md_extruder_switch("off")

    # Stop Z correction thread
    z_thread.stop(); z_thread.join()
    pose[2] += 20; pose = move_to_pose(pose)

    flg = False  # stop after one loop for now
