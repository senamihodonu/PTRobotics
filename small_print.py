# Imports
import sys
import os

# Get the absolute path to the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate to the src directory relative to this file
src_path = os.path.join(current_dir, 'fanuc_ethernet_ip_drivers', 'src')

# Normalize the path and add it to sys.path
sys.path.append(os.path.normpath(src_path))

from robot_controller import robot

# two_dirs_up = os.path.abspath(os.path.join(__file__, "../../.."))
# sys.path.insert(0,two_dirs_up)

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
speed = 2

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

X = 286.206
Y = -290.305
Z = 644.356
W = 0
P = 0.000 
R = -180
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)

X = 286.206+60
Y = -290.305
Z = 644.356
W = 0
P = 0.000 
R = -180
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)


X = 286.206+60
Y = -290.305+609.6
Z = 644.356
W = 0
P = 0.000 
R = -180
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)

X = 286.206
Y = -290.305+609.6
Z = 644.356
W = 0
P = 0.000 
R = -180
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)

X = 286.206
Y = -290.305
Z = 644.356
W = 0
P = 0.000 
R = -180
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)
