# --- Imports ---
import sys
import os

# --- Configure Paths ---
# Get absolute path to the script directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the src path to sys.path for custom modules
src_path = os.path.normpath(os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src"))
sys.path.append(src_path)

# --- Import Custom Modules ---
from robot_controller import robot
from PyPLCConnection import (
    PyPLCConnection,
    LEAD_Y_SCREW, LEAD_Z_SCREW,
    DIP_SWITCH_SETTING_Y, DIP_SWITCH_SETTING_Z,
    GREEN,
    Y_LEFT_MOTION, Y_RIGHT_MOTION,
    Z_DOWN_MOTION, Z_UP_MOTION,
    DISTANCE_SENSOR_IN,
    PLC_IP, ROBOT_IP
)

# --- Initialize Robot ---
print("Small program established")

woody = robot(ROBOT_IP)
speed = 200
woody.set_speed(int(speed))
woody.set_robot_speed_percent(20)

# --- Move to Home Position (Joint Space) ---
# Joint angles in degrees: [J1, J2, J3, J4, J5, J6]
# J1: Base rotation
# J2: Shoulder lift
# J3: Elbow movement
# J4: Wrist roll
# J5: Wrist pitch
# J6: Wrist yaw
print("[HOME] Moving robot to home position")
home_joint_pose = [0, -30, 30, 0, -30, 0]
woody.write_joint_pose(home_joint_pose)

# --- Move to Starting Cartesian Position ---
# Cartesian pose: [X, Y, Z, W, P, R]
# X, Y, Z: Position in millimeters
# W, P, R: Orientation (Roll, Pitch, Yaw) in degrees
start_cartesian_pose = [
    322.637,  # X: Forward/backward
    -2.841,   # Y: Left/right
    847.603,  # Z: Up/down
    180,      # W: Roll
    -90,      # P: Pitch
    0         # R: Yaw
]
woody.write_cartesian_position(start_cartesian_pose)
