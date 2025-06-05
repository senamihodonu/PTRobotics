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
# speed = 200

# woody.set_speed(int(speed))
percent = 100
for x in range(5):
    woody.get_robot_speed_percent(percent)
    percent-=10


