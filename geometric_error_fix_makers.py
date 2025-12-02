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
PRINT_SPEED = 8        # Printing speed (mm/s)
INSIDE_OFFSET = 6       # Offset for inner infill moves (mm)
LAYER_HEIGHT = 4        # Vertical step per layer (mm)
Z_OFFSET = 20           # Safe Z offset for travel moves (mm)
X_OFFSET = 9            # X-axis offset (mm)
PRINT_OFFSET = 5        # Vertical offset between passes (mm)
Z_CORRECTION = 4        # Small Z alignment correction (mm)
TOL = 0                 # Tolerance for Z correction
Z_INCREMENT = LAYER_HEIGHT

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
home_joint_pose = [0,-40, 40, 0, -40, 0]
utils.woody.write_joint_pose(home_joint_pose)

utils.woody.write_joint_pose(home_joint_pose)

home_pose = [0, 0, 0, 46.029, 89.995, 46.028]
utils.woody.write_cartesian_position(home_pose)
print(f"Robot moved to initial pose: {home_pose}")

# Perform pre-motion safety validation
utils.safety_check()

# Raise Z to a safe clearance height
utils.plc.travel(utils.Z_UP_MOTION, 5, 'mm', 'z')
print("Z raised to safe travel height.")
z_pos = 0
pose = [0, 0, z_pos, 46.029, 89.995, 46.028]
# === Surface Height Calibration ===
pose, z_pos = utils.calibrate_height(pose, LAYER_HEIGHT)
time.sleep(2)
print("Height calibration complete.")


# === Z Correction Thread ===
class ZCorrectionThread(threading.Thread):
    def __init__(self, layer_height, tolerance=0.1, interval=2, csv_path=None, z_correction=False):
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
                print_speed = utils.woody.get_speed()

                self.samples.append({
                    'x': x,
                    'y': y,
                    'z': z,
                    'current_height': current_height,
                    'layer_height': LAYER_HEIGHT,
                    'print_speed': print_speed,
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



# # --- Calibration + move setup ---

# calibration_distance = 50
# offset = 0
# pose[0]+= 200

# z_thread = start_z_correction(csv_path=None, layer_height=LAYER_HEIGHT, z_correction=True)
# try:
#     offset = utils.calibrate(
#         calibration_distance,
#         pose,
#         move_axis='y',
#         camera_index=0,
#         save_dir="samples"
#     )
#     print(f"Offset = {offset}")
# finally:
#     stop_z_correction(z_thread)

# time.sleep(1)
# pose = utils.lift_and_travel(pose, calibration_distance, utils.Y_RIGHT_MOTION)
# time.sleep(1)

utils.plc.travel(utils.Y_LEFT_MOTION, 100, 'mm', 'y')
# === Height Calibration ===
pose = [0, 0, z_pos, 46.029, 89.995, 46.028]
pose = utils.move_to_pose(pose, layer_height=LAYER_HEIGHT, tol=TOL)

time.sleep(1)

# === Print Setup ===
utils.plc.md_extruder_switch("on")
time.sleep(2)
z_correct = False
z_thread = start_z_correction(csv_path=None, layer_height=LAYER_HEIGHT, z_correction=z_correct)
utils.woody.set_speed(PRINT_SPEED)
# Move to layer start pose

pose[0] = 100
pose[1] = 500
pose = utils.move_to_pose(pose, layer_height=LAYER_HEIGHT, tol=TOL)

stop_z_correction(z_thread)
time.sleep(1)
pose, z_pos = utils.calibrate_height(pose, LAYER_HEIGHT)
time.sleep(1)

csv_path = "SLP_no_correction_variation_5_per_s_0_tol_1.csv"
flg = True
while flg:

    print(f"\n=== Starting New Layer at Z = {z_pos:.2f} mm ===")

    z_flag = False  # z correction toggle flag
    # Start background Z-correction thread
    z_thread = start_z_correction(csv_path, layer_height=LAYER_HEIGHT, z_correction=z_correct)

    # --- Perimeter Motion Sequence ---
    pose[1] = -500
    pose = utils.move_to_pose(pose, layer_height= LAYER_HEIGHT, tol=TOL, extruding=True, z_correct=z_flag)


#     # # End first extrusion segment
    utils.plc.md_extruder_switch("off")
    stop_z_correction(z_thread)
#     # time.sleep(1)

#     # # Travel to next side of layer
#     # distance = 400 - 2.5
#     # utils.lift_and_travel(pose, distance, utils.Y_LEFT_MOTION)

#     # # Move to second print start location
#     # utils.woody.set_speed(SPEED)
#     # pose[0], pose[1] = 100 - offset, 400
#     # pose = utils.move_to_pose(pose, layer_height=LAYER_HEIGHT, tol=TOL)
#     # time.sleep(1)

#     # # Begin second extrusion pass
#     # utils.woody.set_speed(PRINT_SPEED)
#     # z_thread = start_z_correction(csv_path, layer_height=LAYER_HEIGHT, z_correction=True)

#     # utils.plc.md_extruder_switch("on")
#     # time.sleep(2)

#     # pose[1] = 200
#     # pose = utils.move_to_pose(pose, layer_height= LAYER_HEIGHT, tol=TOL, extruding=True, z_correct=z_flag)

#     # End second pass
#     utils.plc.md_extruder_switch("off")
#     stop_z_correction(z_thread)

#     # Lift Z before moving
#     pose[2] += 20
#     pose = utils.move_to_pose(pose, layer_height=LAYER_HEIGHT, tol=TOL)

#     # Stop loop for now (single-layer testing mode)
    flg = False
