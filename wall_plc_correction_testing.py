# === Imports ===
import sys
import os
import time
import threading
import pandas as pd
import utils  # custom utility module

# === Parameters ===
alignment_calibration = False  # Flag to enable alignment calibration
SPEED = 100             # Robot travel speed (mm/s)
PRINT_SPEED = 10         # Printing speed (mm/s)
INSIDE_OFFSET = 6       # Offset for inner infill moves (mm)
layer_height = 3        # Vertical step per layer (mm)
Z_OFFSET = 20           # Safe Z offset for travel moves (mm)
x_offset = 10            # X-axis offset (mm)
PRINT_OFFSET = 5        # Vertical offset between passes (mm)
Z_CORRECTION = 4        # Small Z alignment correction (mm)
TOL = 1                 # Tolerance for Z correction
travel_offset = 6
check_height_interval = 3  # Interval (s) to check height during print
cummulative_z = layer_height
new_layer_height = 3


class ZLoggingThread(threading.Thread):
    def __init__(self, layer_height, interval=check_height_interval, csv_path=None, log_data=True):
        super().__init__()
        self.layer_height = layer_height
        self.interval = interval
        self.csv_path = csv_path
        self.log_data = log_data   # <--- NEW FLAG
        self._running = threading.Event()
        self._running.set()
        self.samples = []

    def run(self):
        print("[ZLogging] Thread started")
        while self._running.is_set():
            try:
                # Read current pose and sensor data
                pose = utils.woody.read_current_cartesian_pose()
                x, y, z = pose[0], pose[1], pose[2]
                current_height = utils.read_current_z_distance()
                print_speed = utils.woody.get_speed()
                

                # Only log if enabled
                if self.log_data:
                    self.samples.append({
                        'x': x,
                        'y': y,
                        'z': z,
                        'current_height': current_height,
                        'layer_height': self.layer_height,
                        'print_speed': print_speed,
                        'timestamp': time.time()
                    })

            except Exception as e:
                print(f"[ZLogging] Error: {e}")

            time.sleep(self.interval)

    def stop(self):
        """Stop the thread and save samples to CSV if path provided."""
        print("[ZLogging] Thread stopping...")
        self._running.clear()

        # Only save if logging was enabled
        if self.log_data and self.csv_path and self.samples:
            try:
                df = pd.DataFrame(self.samples)
                file_exists = os.path.isfile(self.csv_path)
                df.to_csv(self.csv_path, mode='a', index=False, header=not file_exists)
                print(f"[ZLogging] Appended {len(df)} samples to {self.csv_path}")
            except Exception as e:
                print(f"[ZLogging] Error appending CSV: {e}")


# === Helper Functions ===
def start_z_logging(layer_height, csv_path=None, interval=check_height_interval, log_data=True):
    z_thread = ZLoggingThread(
        layer_height=layer_height,
        interval=interval,
        csv_path=csv_path,
        log_data=log_data
    )
    z_thread.start()
    print("✅ ZLoggingThread started")
    return z_thread


def stop_z_logging(z_thread):
    if z_thread is None:
        print("⚠️ No thread to stop")
        return

    if z_thread.is_alive():
        print("🟡 Stopping ZLoggingThread...")
        z_thread.stop()
        z_thread.join()
        print("✅ ZLoggingThread stopped")
    else:
        print("ℹ️ Thread is not running")


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
utils.plc.configure_z_correction(tolerance=TOL, layer_height=layer_height)
utils.plc.disable_motor(True)
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
time.sleep(0.5)
print("Z raised to safe travel height.")

z_pos = 0
# # === Surface Height Calibration ===

# --- Alignment Calibration ---
if alignment_calibration:
    utils.plc.z_correction('on')
    print("\n=== Starting Alignment Calibration ===")
    pose, z_pos = utils.calibrate_height(pose, layer_height)
    calibration_distance = [400]
    offset = []
    calibration_pose = [200, 0, z_pos, 0, 90, 0]

    # Start Z-correction thread
    z_thread = start_z_logging(layer_height)

    try:
        offset = utils.calibrate(
            calibration_distance,
            calibration_pose,
            move_axis='y',
            camera_index=0,
            save_dir="samples"
        )
        print(f"Offset = {offset}")

    finally:
        stop_z_logging(z_thread)
        utils.plc.z_correction('off')

    print("\n=== Alignment Calibration Complete ===")

    # ------------------------------------------------------------------

print("\n=== Calibrating to Start Print ===")

# Move to start position above print area
pose = [-50,-400, 20, 0, 90, 0]
utils.woody.write_cartesian_position(pose)

time.sleep(0.5)
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
csv_path = "alignment.csv"
flg = True
utils.woody.set_speed(PRINT_SPEED)

# z_thread = start_z_correction(csv_path, layer_height=LAYER_HEIGHT, z_correction=z_correct)
# pose = [200, -400, z_pos, 0, 90, 0]
# utils.woody.write_cartesian_position(pose)
# utils.plc.md_extruder_switch("off")
# stop_z_correction(z_thread)

def safe_print_transition(pose, x, y, z_thread, z_position,travel_speed, print_speed):
    # Turn off extruder before moving
    utils.plc.z_correction('off')
    utils.plc.md_extruder_switch("off")
    utils.woody.set_speed(travel_speed)

    # Disable logging safely
    if z_thread is not None:
        z_thread.log_data = False

    try:
        # Make a copy so we don't mutate the original pose
        pose = pose.copy()

        # Move up to safe Z
        pose[0] = x
        pose[1] = y
        pose[2] += 20
        utils.woody.write_cartesian_position(pose)
        # Switch to print speed
        utils.woody.set_speed(print_speed)
        # Move down to original Z
        time.sleep(0.5)
        pose[2] = z_position
        utils.woody.write_cartesian_position(pose)
    
        # Turn extruder back on
        utils.plc.md_extruder_switch("on")
        utils.plc.z_correction('on')
        time.sleep(3)

    except Exception as e:
        print(f"[safe_print_transition] Error during transition: {e}")

    finally:
        # ALWAYS re-enable logging, even if an error occurred
        if z_thread is not None:
            z_thread.log_data = True

    return pose

z_thread = start_z_logging(
    layer_height=layer_height,
    csv_path=csv_path,
    log_data=True
)
counter = 0

starting_z = z_pos
z_transition_height = layer_height*2  # Height to trigger safe Z travel
print(f"Starting Z: {starting_z}, Transition Height: {z_transition_height}")
end_height = layer_height*4  # Maximum print height



pose = [-60,-350, z_pos, 0, 90, 0]
utils.woody.write_cartesian_position(pose)
time.sleep(1)

utils.plc.md_extruder_switch("on")
utils.plc.z_correction('on')
utils.plc.write_single_register(utils.CUMM_Z_DISPLAY_ADDRESS, cummulative_z)
time.sleep(2)

pose[1] = -400
utils.woody.write_cartesian_position(pose)
    

while flg:
    utils.plc.md_extruder_switch("on")
    utils.plc.z_correction('on')
    time.sleep(1)

    print(f"\n=== Starting New Layer at Z = {z_pos:.2f} mm ===")

    pose[0] = 0
    utils.woody.write_cartesian_position(pose)
    time.sleep(1)
    """                 |
    """                     
    pose[1] = 400
    utils.woody.write_cartesian_position(pose)
    """                 |___________________

    """                     
    pose[0] = 160
    utils.woody.write_cartesian_position(pose)
    """                |___________________
                                           |
                                           |
    """                     
    pose[1] = -400
    utils.woody.write_cartesian_position(pose)
    """                |___________________
                                           |
             ______________________________|
    """ 
    
    pose[0] = 0
    utils.woody.write_cartesian_position(pose)
    """                |___________________
                                           |
             ______________________________|
            |
    """ 
    pose[2] += Z_OFFSET
    utils.woody.write_cartesian_position(pose)
    time.sleep(1)
    utils.plc.md_extruder_switch("off")
    utils.plc.z_correction("off")

    if cummulative_z > 2*layer_height:
        flg = False  # For testing, end after one layer
    
    cummulative_z += 3
    z_pos += 3
    new_layer_height +=3
    utils.plc.configure_z_correction(layer_height=new_layer_height)
    utils.plc.write_single_register(utils.CUMM_Z_DISPLAY_ADDRESS, cummulative_z)
      



stop_z_logging(z_thread)

print("\n=== Program complete ===")