# === Imports ===
import sys
import os
import time
import threading
import pandas as pd

import utils  # custom utility module

# === Parameters ===
alignment_calibration = False  # Flag to enable alignment calibration
SPEED = 200             # Robot travel speed (mm/s)
PRINT_SPEED = 8         # Printing speed (mm/s)
INSIDE_OFFSET = 6       # Offset for inner infill moves (mm)
layer_height = 3        # Vertical step per layer (mm)
Z_OFFSET = 20           # Safe Z offset for travel moves (mm)
x_offset = 9            # X-axis offset (mm)
PRINT_OFFSET = 5        # Vertical offset between passes (mm)
Z_CORRECTION = 4        # Small Z alignment correction (mm)
TOL = 0                 # Tolerance for Z correction
clearance_height = 10   # Clearance height for safe travel moves (mm)

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
                    'layer_height': layer_height,
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
def start_z_correction(csv_path, layer_height = layer_height, z_correction=False):
    """
    Starts Z correction in a background thread.
    """
    # time.sleep(0.5)
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


##################################################################################################################
##################################################################################################################
###################################################################################################################

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
home_joint_pose = [0,-40, 40, 0, -40, 0]
utils.woody.write_joint_pose(home_joint_pose)

pose = [0, 0, 0, 0, 90, 0]
utils.woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")

# Perform pre-motion safety validation
utils.safety_check()
# Raise Z to a safe clearance height
utils.plc.travel(utils.Z_UP_MOTION, 5, 'mm', 'z')
time.sleep(2)
print("Z raised to safe travel height.")

z_pos = 0
# # === Surface Height Calibration ===


# --- Alignment Calibration ---
if alignment_calibration:
    print("\n=== Starting Alignment Calibration ===")
    pose, z_pos = utils.calibrate_height(pose, layer_height)
    calibration_distance = [400]
    offset = []
    caliberation_pose = [200, 0, z_pos, 0, 90, 0]

    # Start Z-correction thread
    z_thread = start_z_correction(
        csv_path=None,
        layer_height=layer_height,
        z_correction=True
    )

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

    # ------------------------------------------------------------------

print("\n=== Calibrating to Start Print ===")

# Move to start position above print area
pose = [-50,-400, 20, 0, 90, 0]
utils.woody.write_cartesian_position(pose)

time.sleep(2)
utils.safety_check()

# Raise Z to a safe clearance height
utils.plc.travel(utils.Z_UP_MOTION, 10, 'mm', 'z')

pose, z_pos = utils.calibrate_height(pose, layer_height)
print("Z raised to safe travel height.")

# Update pose with corrected Z
pose[2] = z_pos
utils.woody.write_cartesian_position(pose)
print("Height calibration complete.")

# === Print Setup ===
z_correct = True  # Enable Z correction during print
csv_path = "alignment.csv"
flg = True
utils.woody.set_speed(PRINT_SPEED)

# z_thread = start_z_correction(csv_path, layer_height=LAYER_HEIGHT, z_correction=z_correct)
# pose = [200, -400, z_pos, 0, 90, 0]
# utils.woody.write_cartesian_position(pose)
# utils.plc.md_extruder_switch("off")
# stop_z_correction(z_thread)

def safe_print_transition(pose, x, y, z, z_thread, clearance_height, travel_speed, print_speed):
    
    utils.plc.md_extruder_switch("off")
    
    utils.woody.set_speed(travel_speed)
    pose[0] = x
    pose[1]= y
    z_thread.layer_height += clearance_height
    utils.woody.write_cartesian_position(pose)
    utils.woody.set_speed(print_speed)
    utils.plc.md_extruder_switch("on")
    z_thread.layer_height -= clearance_height
    utils.woody.write_cartesian_position(pose)
    time.sleep(3)

    return pose

while flg:

    print(f"\n=== Starting New Layer at Z = {z_pos:.2f} mm ===")
    utils.plc.md_extruder_switch("on")
    time.sleep(6)
    # Start background Z-correction thread
    z_thread = start_z_correction(csv_path, layer_height=layer_height, z_correction=z_correct)

    # --- Perimeter Motion Sequence ---
    pose[0] = 0
    utils.woody.write_cartesian_position(pose)
    time.sleep(3)

    pose[1] = 400
    utils.woody.write_cartesian_position(pose)
    pose[0] = 160
    utils.woody.write_cartesian_position(pose)

    pose[1] = -400
    utils.woody.write_cartesian_position(pose)

    pose[0] = 200
    utils.woody.write_cartesian_position(pose)


    pose = safe_print_transition(pose, x=5, y=395, z_thread=z_thread, clearance_height=clearance_height, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # utils.plc.md_extruder_switch("off")
    # utils.woody.set_speed(SPEED)
    # pose[0] = 5
    # pose[1]= 395
    # z_thread.layer_height += clearance_height
    # utils.woody.write_cartesian_position(pose)
    # utils.woody.set_speed(PRINT_SPEED)
    # utils.plc.md_extruder_switch("on")
    # z_thread.layer_height -= clearance_height
    # time.sleep(3)

    pose[0] = 155
    pose[1] = 97.5
    utils.woody.write_cartesian_position(pose)

    pose[0] = 5
    pose[1] = -200
    utils.woody.write_cartesian_position(pose)

    utils.plc.md_extruder_switch("off")
    z_thread.layer_height += clearance_height
    utils.plc.travel(utils.Y_LEFT_MOTION, 400, 'mm', 'y')

    pose = safe_print_transition(pose, x=160, y=0, z_thread=z_thread, clearance_height=clearance_height, travel_speed=SPEED, print_speed=PRINT_SPEED)
    # utils.plc.md_extruder_switch("off")
    # utils.woody.set_speed(SPEED)
    # pose[0] = 160
    # pose[1]= 0
    # utils.woody.write_cartesian_position(pose)
    # z_thread.layer_height += clearance_height
    # utils.woody.set_speed(PRINT_SPEED)
    # utils.plc.md_extruder_switch("on") 
    # z_thread.layer_height -= clearance_height
    # time.sleep(3)

    pose[1] = -400
    utils.woody.write_cartesian_position(pose)

    pose[0] = 0 
    utils.woody.write_cartesian_position(pose)

    pose = safe_print_transition(pose, x=5, y=200, z_thread=z_thread, clearance_height=clearance_height, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # utils.plc.md_extruder_switch("off")
    # utils.woody.set_speed(SPEED)
    # pose[0] = 5
    # pose[1]= 200
    # z_thread.layer_height += clearance_height
    # utils.woody.write_cartesian_position(pose)
    # utils.woody.set_speed(PRINT_SPEED)
    # utils.plc.md_extruder_switch("on")
    # z_thread.layer_height -= clearance_height
    # time.sleep(3)

    pose[0] = 155
    pose[1]= -97.5
    utils.woody.write_cartesian_position(pose)

    pose[0] = 5
    pose[1]= -395
    utils.woody.write_cartesian_position(pose)

    pose = safe_print_transition(pose, x=0, y=400, z_thread=z_thread, clearance_height=clearance_height, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # utils.plc.md_extruder_switch("off")
    # utils.woody.set_speed(SPEED)
    # pose[0] = 0
    # pose[1]= 400
    # z_thread.layer_height += clearance_height
    # utils.woody.write_cartesian_position(pose)
    # utils.woody.set_speed(PRINT_SPEED)
    # utils.plc.md_extruder_switch("on")
    # z_thread.layer_height -= clearance_height
    # utils.woody.write_cartesian_position(pose)
    # time.sleep(3)

    pose[1]= -400
    utils.woody.write_cartesian_position(pose)
    
    pose[0] = 160
    utils.woody.write_cartesian_position(pose)

    pose[1]= 400
    utils.woody.write_cartesian_position(pose)
    
    pose = safe_print_transition(pose, x=0, y=-395, z_thread=z_thread, clearance_height=clearance_height, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # utils.plc.md_extruder_switch("off")
    # utils.woody.set_speed(SPEED)
    # pose[0] = 0
    # pose[1]= -395
    # z_thread.layer_height += clearance_height
    # utils.woody.write_cartesian_position(pose)
    # utils.plc.md_extruder_switch("on")
    # utils.woody.set_speed(PRINT_SPEED)
    # z_thread.layer_height -= clearance_height
    # utils.woody.write_cartesian_position(pose)
    # time.sleep(3)

    pose[0] = 155
    pose[1]= -97.5
    utils.woody.write_cartesian_position(pose)

    pose[0] = 5
    pose[1]= 200
    utils.woody.write_cartesian_position(pose)

    utils.plc.md_extruder_switch("off")

    utils.plc.travel(utils.Y_RIGHT_MOTION, 400, 'mm', 'y')

    pose = safe_print_transition(pose, x=160, y=0, z_thread=z_thread, clearance_height=clearance_height, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # utils.plc.md_extruder_switch("off")
    # utils.woody.set_speed(SPEED)
    # pose[0] = 160
    # pose[1]= 0
    # z_thread.layer_height += clearance_height
    # utils.woody.write_cartesian_position(pose)
    # utils.woody.set_speed(PRINT_SPEED)
    # utils.plc.md_extruder_switch("on")
    # z_thread.layer_height -= clearance_height 
    # time.sleep(3)

    pose[1] = 400
    utils.woody.write_cartesian_position(pose)

    pose[0] = 0 
    utils.woody.write_cartesian_position(pose)  

    pose[1] = 0
    utils.woody.write_cartesian_position(pose)

    pose = safe_print_transition(pose, x=5, y=-200, z_thread=z_thread, clearance_height=clearance_height, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # utils.plc.md_extruder_switch("off")
    # utils.woody.set_speed(SPEED)
    # pose[0] = 5
    # pose[1] = -200
    # z_thread.layer_height += clearance_height
    # utils.woody.write_cartesian_position(pose)
    # utils.woody.set_speed(PRINT_SPEED)
    # utils.plc.md_extruder_switch("on")
    # z_thread.layer_height -= clearance_height
    # time.sleep(3)

    pose[0]= 155
    pose[1]= 97.5
    utils.woody.write_cartesian_position(pose)

    pose[0]= 5
    pose[1]= 395
    utils.woody.write_cartesian_position(pose)  

    utils.plc.md_extruder_switch("off")

    stop_z_correction(z_thread)
   

    flg = False

print("\n=== Program complete ===")