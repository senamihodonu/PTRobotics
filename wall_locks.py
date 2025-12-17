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
PRINT_SPEED = 8         # Printing speed (mm/s)
INSIDE_OFFSET = 6       # Offset for inner infill moves (mm)
layer_height = 3        # Vertical step per layer (mm)
Z_OFFSET = 20           # Safe Z offset for travel moves (mm)
x_offset = 10           # X-axis offset (mm)
PRINT_OFFSET = 5        # Vertical offset between passes (mm)
Z_CORRECTION = 4        # Small Z alignment correction (mm)
TOL = 1                 # Tolerance for Z correction
travel_offset = 6
check_height_interval = 3  # Interval (s) to check height during print

plc_lock = threading.Lock()
robot_lock = threading.Lock()

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
        # self.z_correction_event = threading.Event()
        # if z_correction:
        #         self.z_correction_event.set()


    def run(self):
        print("[ZCorrection] Thread started")
        while self._running.is_set():
            try:
                if self.z_correction:
                # if self.z_correction_event.is_set():
                    # Perform gantry Z correction
                    with plc_lock:
                        utils.apply_z_correction_gantry(self.layer_height, tolerance=self.tolerance)

                # Record current position and sensor height
                with robot_lock:
                    pose = utils.woody.read_current_cartesian_pose()
                    print_speed = utils.woody.get_speed()

                x, y, z = pose[0], pose[1], pose[2]

                with plc_lock:
                    current_height = utils.read_current_z_distance()

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
    """
    Starts Z correction in a background thread.
    """
    z_thread = ZCorrectionThread(
        layer_height,
        tolerance=TOL,
        interval=check_height_interval,
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
with robot_lock:
    utils.woody.set_robot_uframe(utils.MD_PELLET_UFRAME)     # Select pellet extruder user frame
    utils.woody.set_robot_utool(utils.MD_PELLET_UTOOL)       # Select pellet extruder tool frame
    utils.woody.set_speed(SPEED)                             # Set travel speed (mm/s)

# Reset PLC output states
with plc_lock:
    utils.plc.reset_coils()
    utils.plc.disable_motor(True)
    utils.plc.md_extruder_switch("off")

time.sleep(2)

with plc_lock:
    utils.plc.disable_motor(False)

print("System parameters configured.")

# === Initial Position Setup ===
home_joint_pose = [0,-40, 40, 0, -40, 0]
with robot_lock:
    utils.woody.write_joint_pose(home_joint_pose)

pose = [0, 0, 0, 0, 90, 0]
with robot_lock:
    utils.woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")

# Perform pre-motion safety validation
utils.safety_check()

# Raise Z to a safe clearance height
with plc_lock:
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
with robot_lock:
    utils.woody.write_cartesian_position(pose)

time.sleep(2)
utils.safety_check()

# Raise Z to a safe clearance height
with plc_lock:
    utils.plc.travel(utils.Z_UP_MOTION, 5, 'mm', 'z')

pose, z_pos = utils.calibrate_height(pose, layer_height)
print("Z raised to safe travel height.")

# Update pose with corrected Z
pose[2] = z_pos
with robot_lock:
    utils.woody.write_cartesian_position(pose)
print("Height calibration complete.")

# === Print Setup ===
z_correct = True  # Enable Z correction during print
csv_path = "alignment.csv"
flg = True
with robot_lock:
    utils.woody.set_speed(PRINT_SPEED)

# z_thread = start_z_correction(csv_path, layer_height=LAYER_HEIGHT, z_correction=z_correct)
# pose = [200, -400, z_pos, 0, 90, 0]
# utils.woody.write_cartesian_position(pose)
# utils.plc.md_extruder_switch("off")
# stop_z_correction(z_thread)

def safe_print_transition(pose, x, y, z_position, z_thread, travel_speed, print_speed):
    time.sleep(1)
    with plc_lock:
        utils.plc.md_extruder_switch("off")
    with robot_lock:
        utils.woody.set_speed(travel_speed)

    z_thread.z_correction = False
    # z_thread.z_correction_event.clear()

    pose[0] = x
    pose[1]= y
    pose[2] += Z_OFFSET
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    pose[2] -= Z_OFFSET
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    time.sleep(1)
    with robot_lock:
        utils.woody.set_speed(print_speed)
    pose[2] = z_position
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    time.sleep(1)
    with plc_lock:
        utils.plc.md_extruder_switch("on")
    z_thread.z_correction = True
    # z_thread.z_correction_event.set()

    time.sleep(2)
    return pose

z_thread = start_z_correction(csv_path, layer_height=layer_height, z_correction=z_correct)

counter = 0
cummulative_z = 0
starting_z = z_pos
z_transition_height = layer_height*2  # Height to trigger safe Z travel
print(f"Starting Z: {starting_z}, Transition Height: {z_transition_height}")
end_height = layer_height*4  # Maximum print height

while flg:

    print(f"\n=== Starting New Layer at Z = {z_pos:.2f} mm ===")
    with plc_lock:
        utils.plc.md_extruder_switch("on")
    time.sleep(4)

    pose[0] = 0
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    time.sleep(2)
    """                 |
    """
    pose[1] = 400
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """                 |___________________

    """
    pose[0] = 160
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """                |___________________
                                           |
                                           |
    """
    pose[1] = -400
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """                |___________________
                                           |
             ______________________________|
    """

    pose = safe_print_transition(pose, x=5, y=395, z_position=z_pos, z_thread=z_thread,
                                 travel_speed=SPEED, print_speed=PRINT_SPEED)

    # start infill
    pose[0] = 155
    pose[1] = 97.5
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """                |__________________
                                         /|
                                       /  |
             ________________________/____|
            |
    """

    pose[0] = 5
    pose[1] = -200
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """                |___________________
                                \         /|
                                  \     /  |
             _______________________\_/____|
            |
    """

    pose[0] = 155
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """                |___________________
                               | \         /|
                               |   \     /  |
             __________________|_____\_/____|
            |
    """

    with plc_lock:
        utils.plc.md_extruder_switch("off")
    z_thread.z_correction = False
    # z_thread.z_correction_event.clear()

    pose[2] += Z_OFFSET
    with robot_lock:
        utils.woody.write_cartesian_position(pose)

    with plc_lock:
        utils.plc.travel(utils.Y_LEFT_MOTION, 400, 'mm', 'y')
    """                |___________________
                               | \         /|
                               |   \     /  |
             __________________|_____\_/____|
            |
            <-----------------
            400 mm robot left travel
    """

    pose = safe_print_transition(pose, x=160-x_offset, y=travel_offset, z_position=z_pos, z_thread=z_thread,
                                 travel_speed=SPEED, print_speed=PRINT_SPEED)

    pose[1] = -400
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """                |____________________
                               | \         /|
                               |   \     /  |
    ________ __________________|_____\_/____|
            |
    """

    pose[0] = 0-x_offset
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """                |____________________
    |                          | \         /|
    |                          |   \     /  |
    |_______ __________________|_____\_/____|
            |
    """

    pose[1] = 0+travel_offset
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
     _________|______________
    |             |\        /|
    |             | \     /  |
    |_________ ___|____\_/___|
              |
    """
    pose = safe_print_transition(pose, x=5-x_offset, y=200, z_position=z_pos, z_thread=z_thread,
                                 travel_speed=SPEED, print_speed=PRINT_SPEED)

    # start infill
    pose[0] = 155-x_offset
    pose[1]= -97.5
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
     __________|___________
    |          /|\        /|
    |        /  |  \     / |
    |______/__ _|____\_/___|
              |
    """

    pose[0] = 5-x_offset
    pose[1]= -395
    with robot_lock:
        utils.woody.write_cartesian_position(pose)

    # Increment the absolute Z position for the next layer
    z_thread.z_correction = False
    # z_thread.z_correction_event.clear()

    pose[0] = 0-x_offset
    pose[1]= 400
    pose[2] += Z_OFFSET
    with robot_lock:
        utils.woody.write_cartesian_position(pose)

    pose[2] += Z_OFFSET
    with robot_lock:
        utils.woody.write_cartesian_position(pose)

    z_pos += layer_height
    cummulative_z += layer_height

    # Increase the layer_height variable itself for the following iteration
    layer_height += 3
    z_thread.layer_height = layer_height

    pose = safe_print_transition(
        pose,
        x=0-x_offset,
        y=400,
        z_position=z_pos,
        z_thread=z_thread,
        travel_speed=SPEED,
        print_speed=PRINT_SPEED
    )

    pose[1]= -400
    with robot_lock:
        utils.woody.write_cartesian_position(pose)

    """
    ___________________
     __________|____________
    |\         /  \        /|
    |  \     /     \     /  |
    |___ \_/__ _______\_/___|
              |
    """
    pose[0] = 160-x_offset
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
    ___________________
   |      __________|____________
   |     |\         /  \        /|
   |     |  \     /     \     /  |
   |     |___ \_/__ _______\_/___|
   |             |
    """

    pose[1]= 400
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
    ------------------
   |      __________|____________
   |     |\         /  \        /|
   |     |  \     /     \     /  |
   |     |___ \_/__ _______\_/___|
   |             |
    ------------------
    """

    pose = safe_print_transition(pose, x=5-x_offset, y=-395, z_position=z_pos, z_thread=z_thread,
                                 travel_speed=SPEED, print_speed=PRINT_SPEED)

    pose[0] = 155-x_offset
    pose[1]= -97.5
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
    ------------------
   | \    __________|____________
   |   \ |\         /  \        /|
   |     |  \     /     \     /  |
   |     |___ \_/__ _______\_/___|
   |             |
    ------------\-----
   """

    pose[0] = 5-x_offset
    pose[1]= 200+x_offset
    with robot_lock:
        utils.woody.write_cartesian_position(pose)

    """
    -------------------/
   | \    __________|____________
   |   \ |\         /  \        /|
   |     |  \     /     \     /  |
   |     |___ \_/__ _______\_/___|
   |             |
    ------------\/-----
   """
    pose[0] = 155-x_offset
    with robot_lock:
        utils.woody.write_cartesian_position(pose)

    with plc_lock:
        utils.plc.md_extruder_switch("off")
    z_thread.z_correction = False
    # z_thread.z_correction_event.clear()
    pose[2] += Z_OFFSET
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    with plc_lock:
        utils.plc.travel(utils.Y_RIGHT_MOTION, 400, 'mm', 'y')
    """
    -------------------/
   | \    __________|____________
   |   \ |\         /  \        /|
   |     |  \     /     \     /  |
   |     |___ \_/__ _______\_/___|
   |             |
    ------------\/-----
    ----------------->
    400 mm robot right travel
   """

    pose = safe_print_transition(pose, x=160, y=0, z_position=z_pos, z_thread=z_thread,
                                 travel_speed=SPEED, print_speed=PRINT_SPEED)

    pose[1] = 400
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
    -------------------/
   | \    __________|____________
   |   \ |\         /  \        /|
   |     |  \     /     \     /  |
   |     |___ \_/__ _______\_/___|
   |             |
    ------------\/-------------------
   """

    pose[0] = 0
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
    -------------------/
   | \    __________|____________    |
   |   \ |\         /  \        /|   |
   |     |  \     /     \     /  |   |
   |     |___ \_/__ _______\_/___|   |
   |             |                   |
    ------------\--------------------
   """

    pose[1] = 0
    with robot_lock:
        utils.woody.write_cartesian_position(pose)

    """
    -------------------/-------------
   | \    __________|____________    |
   |   \ |\         /  \        /|   |
   |     |  \     /     \     /  |   |
   |     |___ \_/__ _______\_/___|   |
   |             |                   |
    ------------\--------------------
   """

    pose = safe_print_transition(pose, x=5, y=-200, z_position=z_pos, z_thread=z_thread,
                                 travel_speed=SPEED, print_speed=PRINT_SPEED)

    # start infill
    pose[0]= 155
    pose[1]= 97.5
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
    -------------------/\-------------
   | \    __________|____________     |
   |   \ |\         /  \         /|   |
   |     |  \     /      \     /  |   |
   |     |___ \_/__ ______ \_/____|   |
   |             |                    |
    ------------\/-----------\--------
   """

    pose[0]= 5
    pose[1]= 395
    with robot_lock:
        utils.woody.write_cartesian_position(pose)
    """
    -------------------/\---------------
   | \    __________|_____________    / |
   |   \ |\         /  \         /| /   |
   |     |  \     /      \     /  |     |
   |     |___ \_/__ ______ \_/____|     |
   |             |                      |
    ------------\/------------\/--------
   """

    with plc_lock:
        utils.plc.md_extruder_switch("off")
    flg = False  # For testing, end after one layer

stop_z_correction(z_thread)

print("\n=== Program complete ===")
