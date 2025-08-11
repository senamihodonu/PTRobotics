# Imports
import sys
import os
import time

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

plc = PyPLCConnection(PLC_IP)
speed = 200

# Set Y axis speed
plc.calculate_pulse_per_second(speed, DIP_SWITCH_SETTING_Y, LEAD_Y_SCREW, 'y')
print(f"[INFO] PLC Y-axis speed configured to {speed} mm/min")
# Set Z axis speed
# plc.calculate_pulses_per_second(z_speed, DIP_SWITCH_SETTING_Z, LEAD_Z_SCREW, 'z')

# # Ensure initial positioning
# while plc.read_modbus_coils(8) == True or plc.read_modbus_coils(9) == True or plc.read_modbus_coils(14) == True:
#     plc.write_modbus_coils(Z_DOWN_MOTION, True)
#     plc.write_modbus_coils(Y_RIGHT_MOTION,True)
# plc.write_modbus_coils(Z_DOWN_MOTION, False)
# plc.write_modbus_coils(Y_RIGHT_MOTION,False)
# time.sleep(1)

woody = robot(ROBOT_IP)
speed = 200

woody.set_speed(int(speed))
woody.set_robot_speed_percent(50)
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

distance = 100
plc.travel(Y_LEFT_MOTION, distance, "mm", speed)

# Z = -0

# for x in range(10):
#     # starting cartesian position
#     X = -0
#     Y = -0
#     W = -0
#     P = 90
#     R = 0
#     pose=[X, Y, Z, W, P, R]
#     woody.write_cartesian_position(pose)

#     # starting cartesian position
#     X = 0
#     Y = 200
#     pose=[X, Y, Z, W, P, R]
#     woody.write_cartesian_position(pose)

#     # starting cartesian position
#     X = -100
#     pose=[X, Y, Z, W, P, R]
#     woody.write_cartesian_position(pose)

#     # starting cartesian position
#     Y = -200
#     pose=[X, Y, Z, W, P, R]
#     woody.write_cartesian_position(pose)

#     # starting cartesian position
#     X = 0
#     pose=[X, Y, Z, W, P, R]
#     woody.write_cartesian_position(pose)

#     # starting cartesian position
#     Y = 0
#     pose=[X, Y, Z, W, P, R]
#     woody.write_cartesian_position(pose)

#     Z += 3.5

# # starting cartesian position
# X = -100
# Y = -400
# Z = 0
# W = 180
# P = 90
# R = 180
# pose=[X, Y, Z, W, P, R]
# woody.write_cartesian_position(pose)
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


# distance = 20
# speed = 5
# plc.travel(Z_DOWN_MOTION, distance, "mm", speed)