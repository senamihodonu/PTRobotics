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
PRINT_SPEED = 20        # Printing speed (mm/s)
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
utils.safety_check()
utils.plc.travel(utils.Z_UP_MOTION, 5, 'mm', 'z')


# === Height Calibration ===
pose, z = utils.calibrate_height(pose, LAYER_HEIGHT+10)
time.sleep(2)





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

# === Helper Functions ===
def start_z_correction(csv_path, layer_height = LAYER_HEIGHT, z_correction=False):
    """
    Starts Z correction in a background thread.
    """
    z_thread = ZCorrectionThread(
        layer_height,
        tolerance=1,
        interval=2,
        csv_path=csv_path,
        z_correction=z_correction
    )
    z_thread.start()
    print("✅ Z correction thread started.")
    return z_thread


def stop_z_correction(z_thread):
    """
    Stops the Z correction thread safely and provides feedback.
    """
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



# === Print Setup ===
utils.plc.md_extruder_switch("on")
print("Extruder ON, starting print sequence...")
time.sleep(4)

# === Printing Loop (single-layer example) ===
flg = True
layer = 0
caliberate = True
layer_height = LAYER_HEIGHT

csv_path = "z_correction1.csv"
caliberate_height = LAYER_HEIGHT+10
z_thread = start_z_correction(csv_path, caliberate_height, z_correction=True)
calibration_distance = 50
base_pose = [200, 0, z, 0, 90, 0]
utils.calibrate(calibration_distance, base_pose, move_axis='y', camera_index=0, save_dir="samples")
time.sleep(2)
stop_z_correction(z_thread)
utils.plc.travel(utils.Y_RIGHT_MOTION, calibration_distance, "mm", axis="y")


# === Height Calibration ===
pose, z = utils.calibrate_height(pose, LAYER_HEIGHT)
time.sleep(2)

# while flg:
#     z_flag = False
#     print(f"\n=== Starting new layer at z = {z:.2f} mm ===")

#     pose = [-100, 0, z, 0, 90, 0]
#     pose = move_to_pose(pose)

#     # Start perimeter path
#     utils.woody.set_speed(PRINT_SPEED)
#     utils.plc.md_extruder_switch("on")
#     time.sleep(3)
#     print("Extruder ON for perimeter path.")

#     # # Start Z correction in background
#     # z_thread = ZCorrectionThread(LAYER_HEIGHT, tolerance=1, interval=2, csv_path="z_correction1.csv", z_correction=True)
#     # z_thread.start()

#     z_thread = start_z_correction(csv_path, layer_height=LAYER_HEIGHT, z_correction=True)


#     # Example X/Y moves for perimeter
#     pose[0] = 150; pose[1] = 400; pose = move_to_pose(pose, extruding=False, z_correct=z_flag)

#     pose[1] = 300; pose = move_to_pose(pose, extruding=True, z_correct=z_flag)



#     utils.plc.md_extruder_switch("off")

#     # Stop Z correction thread
#     # z_thread.stop(); z_thread.join()
#     stop_z_correction(z_thread)
#     pose[2] += 20; pose = move_to_pose(pose)

#     flg = False  # stop after one loop for now
