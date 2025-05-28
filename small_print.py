# Imports
import sys
import os

# Get the absolute path to the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate to the fanuc_ethernet_ip_drivers/src directory
src_path = os.path.normpath(
    os.path.join(current_dir, "..", "fanuc_ethernet_ip_drivers", "src")
)

# Add the src path to sys.path
sys.path.append(src_path)

from robot_controller import robot

# Get the absolute path to the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate to the fanuc_ethernet_ip_drivers/src directory
src_path = os.path.normpath(
    os.path.join(current_dir, "..", "fanuc_ethernet_ip_drivers", "src")
)

# Add the src path to sys.path
sys.path.append(src_path)

from PyPLCConnection import (
    PyPLCConnection,
    LEAD_Y_SCREW, LEAD_Z_SCREW,
    DIP_SWITCH_SETTING_Y,
    GREEN,
    Y_LEFT_MOTION, Y_RIGHT_MOTION,
    Z_DOWN_MOTION, Z_UP_MOTION,
    DISTANCE_SENSOR_IN,
    DIP_SWITCH_SETTING_Z,
    PLC_IP,
    ROBOT_IP
)


print("Small program established")

woody = robot(ROBOT_IP)
speed = 200

woody.set_speed(int(speed))

# --- Home Position ---
print("[HOME] Moving robot to home position")
J1= -45.407
J2= -5.782
J3= 12.716
J4= 0
J5= 77.284
J6= -45.407
pose=[J1, J2, J3, J4, J5, J6]
woody.write_joint_pose(pose)

# Cartesian movements
positions = [
    (286.206, -290.305, 644.356),
    (286.206 + 60, -290.305, 644.356),
    (286.206 + 60, -290.305 + 609.6, 644.356),
    (286.206, -290.305 + 609.6, 644.356),
    (286.206, -290.305, 644.356)
]

for X, Y, Z in positions:
    pose = [X, Y, Z, 0, 0.000, -180]
    woody.write_cartesian_position(pose)