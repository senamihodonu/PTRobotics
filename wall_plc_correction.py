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
x_offset = 10            # X-axis offset (mm)
PRINT_OFFSET = 5        # Vertical offset between passes (mm)
Z_CORRECTION = 4        # Small Z alignment correction (mm)
TOL = 2                 # Tolerance for Z correction
travel_offset = 6
check_height_interval = 3  # Interval (s) to check height during print


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
utils.plc.travel(utils.Z_UP_MOTION, 5, 'mm', 'z')

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

def safe_print_transition(pose, x, y, z_thread, travel_speed, print_speed):
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
        # Move down to original Z
        pose[2] -= 20
        utils.woody.write_cartesian_position(pose)
        # Switch to print speed
        utils.woody.set_speed(print_speed)

        time.sleep(0.5)

        # Turn extruder back on
        utils.plc.md_extruder_switch("on")
        utils.plc.z_correction('on')

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
cummulative_z = 0
starting_z = z_pos
z_transition_height = layer_height*2  # Height to trigger safe Z travel
print(f"Starting Z: {starting_z}, Transition Height: {z_transition_height}")
end_height = layer_height*4  # Maximum print height

pose = [-70,-400, z_pos, 0, 90, 0]
utils.woody.write_cartesian_position(pose)

while flg:
    utils.plc.z_correction('on')
    print(f"\n=== Starting New Layer at Z = {z_pos:.2f} mm ===")
    utils.plc.md_extruder_switch("on")
    time.sleep(4)
             

    pose[0] = 0
    utils.woody.write_cartesian_position(pose)
    time.sleep(2)
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
    
    pose = safe_print_transition(pose, x=5, y=395, z_position=z_pos, z_thread=z_thread, travel_speed=SPEED, print_speed=PRINT_SPEED)

    # start infill
    pose[0] = 155
    pose[1] = 97.5
    utils.woody.write_cartesian_position(pose)
    """                |__________________
                                         /|
                                       /  |
             ________________________/____|
            |
    """ 

    pose[0] = 5
    pose[1] = -200
    utils.woody.write_cartesian_position(pose)
    """                |___________________
                                \         /|
                                  \     /  |
             _______________________\_/____|
            |
    """ 

    pose[0] = 155
    utils.woody.write_cartesian_position(pose)
    """                |___________________
                               | \         /|
                               |   \     /  |
             __________________|_____\_/____|
            |
    """ 

    utils.plc.md_extruder_switch("off")
    utils.plc.z_correction("off")
    z_thread.log_data = False
    pose[2] += Z_OFFSET
    utils.woody.write_cartesian_position(pose)

    utils.plc.travel(utils.Y_LEFT_MOTION, 400, 'mm', 'y')
    """                |___________________
                               | \         /|
                               |   \     /  |
             __________________|_____\_/____|
            |
            <-----------------
            400 mm robot left travel
    """ 
    
    # turn off extruder
    # increase speed for travel
    # set next x position
    # set next y position
    # set back to print speed
    # turn on extruder
    # restore print Z
    
    pose = safe_print_transition(
        pose,
        x=160 - x_offset,
        y=travel_offset,
        z_thread=z_thread,
        travel_speed=SPEED,
        print_speed=PRINT_SPEED
    )


    pose[1] = -400
    utils.woody.write_cartesian_position(pose)
    """                |____________________
                               | \         /|
                               |   \     /  |
    ________ __________________|_____\_/____|
            |
    """ 

    pose[0] = 0-x_offset 
    utils.woody.write_cartesian_position(pose)
    """                |____________________
    |                          | \         /|
    |                          |   \     /  |
    |_______ __________________|_____\_/____|
            |
    """ 

    pose[1] = 0+travel_offset 
    utils.woody.write_cartesian_position(pose)
    """
     _________|______________
    |             |\        /|
    |             | \     /  |
    |_________ ___|____\_/___|
              |
    """ 
    pose = safe_print_transition(
    pose,
    x=5 - x_offset,
    y=200,
    z_thread=z_thread,
    travel_speed=SPEED,
    print_speed=PRINT_SPEED
    )

    # start infill
    pose[0] = 155-x_offset
    pose[1]= -97.5
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
    utils.woody.write_cartesian_position(pose)
    """
     __________|____________
    |\         /  \        /|
    |  \     /     \     /  |
    |___ \_/__ _______\_/___|
              |
    """ 

    # Increment the absolute Z position for the next layer
    z_thread.log_data = False
    pose[0] = 0-x_offset
    pose[1]= 400
    pose[2] += Z_OFFSET
    utils.woody.write_cartesian_position(pose)

#     z_pos += layer_height
#     cummulative_z += layer_height

#     # Increase the layer_height variable itself for the following iteration
#     layer_height += 3
#     z_thread.layer_height = layer_height


#     # Move to a safe transition point before starting the next print sequence
#     # - x=0, y=400 → target transition coordinates
#     # - z_thread → active Z-correction thread
#     # - clearance_height → lift amount for safe travel
#     # - SPEED / PRINT_SPEED → travel vs. printing speeds
#     pose = safe_print_transition(
#         pose,
#         x=0-x_offset,
#         y=400,
#         z_thread=z_thread,
#         travel_speed=SPEED,
#         print_speed=PRINT_SPEED
#     )

#     pose[1]= -400
#     utils.woody.write_cartesian_position(pose)


#     """
#     ___________________            
#      __________|____________
#     |\         /  \        /|
#     |  \     /     \     /  |
#     |___ \_/__ _______\_/___|
#               |
#     """ 
#     pose[0] = 160-x_offset
#     utils.woody.write_cartesian_position(pose)
#     """
#     ___________________            
#    |      __________|____________
#    |     |\         /  \        /|
#    |     |  \     /     \     /  |
#    |     |___ \_/__ _______\_/___|
#    |             |
#     """ 

#     pose[1]= 400
#     utils.woody.write_cartesian_position(pose)
#     """
#     ------------------            
#    |      __________|____________
#    |     |\         /  \        /|
#    |     |  \     /     \     /  |
#    |     |___ \_/__ _______\_/___|
#    |             |
#     ------------------
#     """ 

#     pose = safe_print_transition(
#         pose,
#         x=5 - x_offset,
#         y=-395,
#         z_thread=z_thread,
#         travel_speed=SPEED,
#         print_speed=PRINT_SPEED
#     )


#     pose[0] = 155-x_offset
#     pose[1]= -97.5
#     utils.woody.write_cartesian_position(pose)
#     """
#     ------------------            
#    | \    __________|____________
#    |   \ |\         /  \        /|
#    |     |  \     /     \     /  |
#    |     |___ \_/__ _______\_/___|
#    |             |
#     ------------\-----
#    """ 

#     pose[0] = 5-x_offset
#     pose[1]= 200+x_offset
#     utils.woody.write_cartesian_position(pose)

#     """
#     -------------------/            
#    | \    __________|____________
#    |   \ |\         /  \        /|
#    |     |  \     /     \     /  |
#    |     |___ \_/__ _______\_/___|
#    |             |
#     ------------\/-----
#    """ 
#     pose[0] = 155-x_offset
#     utils.woody.write_cartesian_position(pose)

#     utils.plc.md_extruder_switch("off")   
#     z_thread.z_correction = False
#     pose[2] += Z_OFFSET
#     utils.woody.write_cartesian_position(pose)
#     utils.plc.travel(utils.Y_RIGHT_MOTION, 400, 'mm', 'y')
#     """
#     -------------------/            
#    | \    __________|____________
#    |   \ |\         /  \        /|
#    |     |  \     /     \     /  |
#    |     |___ \_/__ _______\_/___|
#    |             |
#     ------------\/-----
#     ----------------->
#     400 mm robot right travel
#    """ 

#     pose = safe_print_transition(
#     pose,
#     x=160,
#     y=0,
#     z_thread=z_thread,
#     travel_speed=SPEED,
#     print_speed=PRINT_SPEED
# )

#     pose[1] = 400
#     utils.woody.write_cartesian_position(pose)
#     """
#     -------------------/            
#    | \    __________|____________
#    |   \ |\         /  \        /|
#    |     |  \     /     \     /  |
#    |     |___ \_/__ _______\_/___|
#    |             |                   
#     ------------\/-------------------
#    """ 

#     pose[0] = 0 
#     utils.woody.write_cartesian_position(pose)  
#     """
#     -------------------/            
#    | \    __________|____________    |
#    |   \ |\         /  \        /|   |
#    |     |  \     /     \     /  |   |
#    |     |___ \_/__ _______\_/___|   |
#    |             |                   |
#     ------------\--------------------
#    """ 

#     pose[1] = 0
#     utils.woody.write_cartesian_position(pose)

#     """
#     -------------------/-------------            
#    | \    __________|____________    |
#    |   \ |\         /  \        /|   |
#    |     |  \     /     \     /  |   |
#    |     |___ \_/__ _______\_/___|   |
#    |             |                   |
#     ------------\--------------------
#    """ 

#     pose = safe_print_transition(pose, x=5, y=-200, z_position=z_pos, z_thread=z_thread, travel_speed=SPEED, print_speed=PRINT_SPEED)

#     # start infill
#     pose[0]= 155
#     pose[1]= 97.5
#     utils.woody.write_cartesian_position(pose)
#     """
#     -------------------/\-------------            
#    | \    __________|____________     |
#    |   \ |\         /  \         /|   |
#    |     |  \     /      \     /  |   |
#    |     |___ \_/__ ______ \_/____|   |
#    |             |                    |
#     ------------\/-----------\--------
#    """ 

#     pose[0]= 5
#     pose[1]= 395
#     utils.woody.write_cartesian_position(pose)  
#     """
#     -------------------/\---------------            
#    | \    __________|_____________    / |
#    |   \ |\         /  \         /| /   |
#    |     |  \     /      \     /  |     |
#    |     |___ \_/__ ______ \_/____|     |
#    |             |                      |
#     ------------\/------------\/--------
#    """ 
    

    utils.plc.md_extruder_switch("off")
    utils.plc.z_correction("off")
    flg = False  # For testing, end after one layer


stop_z_logging(z_thread)

print("\n=== Program complete ===")