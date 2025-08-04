# Imports
import sys
import os

# Get the absolute path to the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate to the fanuc_ethernet_ip_drivers/src directory
src_path = os.path.normpath(
    os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src")
)

# Add the src path to sys.path
sys.path.append(src_path)

from robot_controller import robot

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
woody.set_robot_speed_percent(20)
# --- Home Position ---
print("[HOME] Moving robot to home position")
J1= 0
J2= -30
J3= 30
J4= 0
J5= -30
J6= 0
pose=[J1, J2, J3, J4, J5, J6]
woody.write_joint_pose(pose)

# starting cartesian position
X = 322.637
Y = -2.841
Z = 847.603
W = 180
P = -90
R = 0
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)



# # # Cartesian movements

# starting_x = 286.206-10
# starting_y = -290.305
# starting_z = 644.356

# for x in range(1):
#     positions = [
#         (starting_x, starting_y, starting_z),
#         (starting_x + 50, starting_y, starting_z),
#         (starting_x + 50, starting_y + 609.6, starting_z),
#         (starting_x, starting_y + 609.6, starting_z),
#         (starting_x, starting_y, starting_z)
#     ]

#     for X, Y, Z in positions:
#         pose = [X, Y, Z, W, P, R]
#         woody.write_cartesian_position(pose)
    
#     starting_z -= 15

# plc = PyPLCConnection(PLC_IP)
# distance = 308/4
# speed = 5
# plc.travel(Y_RIGHT_MOTION, distance, "mm", speed)