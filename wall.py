# Imports
import sys
import os

# Get the absolute path to the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate to the src directory relative to this file
src_path = os.path.join(current_dir, '..', 'fanuc_ethernet_ip_drivers', 'src')

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
    DIP_SWITCH_SETTING_Z
)


print("Wall program established")
 
ip = "172.29.183.59"
plc_ip= "192.168.1.25"
robot_ip = '192.168.1.101' #Woody

#establish connection between PLC and Python
plc = PyPLCConnection(plc_ip)
woody = robot(robot_ip)


# Turn ON green light and OFF yellow/red at start
plc.write_modbus_coils(GREEN, False)
# plc.write_modbus_coils(YELLOW_LIGHT, False)
# plc.write_modbus_coils(RED_LIGHT, False)

# Set robot speed
speed = 200
z_speed = 45 
layer_height = 15
z_transition = 415
transition_distance = 0
# woody.set_speed(int(speed))
print("Speed set at " + str(speed) + " mm/min")

# Set Y axis speed
plc.calculate_pulse_per_second(speed, DIP_SWITCH_SETTING_Y, LEAD_Y_SCREW, 'y')
print(f"[INFO] PLC Y-axis speed configured to {speed} mm/min")
# Set Z axis speed
# plc.calculate_pulses_per_second(z_speed, DIP_SWITCH_SETTING_Z, LEAD_Z_SCREW, 'z')

plc.travel(Z_UP_MOTION, 10, "mm", z_speed)


# --- Home Position ---
print("[HOME] Moving robot to home position")
J1= 0
J2= -60
J3= 0
J4= 0.000
J5= 90
J6= 0.000
pose=[J1, J2, J3, J4, J5, J6]
woody.write_joint_pose(pose)


# Ensure initial positioning
while plc.read_modbus_coils(8) == True or plc.read_modbus_coils(9) == True or plc.read_modbus_coils(14) == True:
    plc.write_modbus_coils(Z_DOWN_MOTION, True)
    plc.write_modbus_coils(Y_RIGHT_MOTION,True)
plc.write_modbus_coils(Z_DOWN_MOTION, False)
plc.write_modbus_coils(Y_RIGHT_MOTION,False)
time.sleep(1)

translation_distance = 0
print(f"Current position {translation_distance}")

distance = 1
translation_distance += distance
plc.travel(Y_LEFT_MOTION, distance, "inches", speed)
print(f"Current position {translation_distance}")

# starting home position
print("Program start position")
J1=  -64.92
J2= -17.408
J3= -3.901
J4= 0.000
J5= 93.901
J6= -64.92
pose=[J1, J2, J3, J4, J5, J6]
woody.write_joint_pose(pose)

# starting cartesian position
X = 144.023
Y = -307.737
Z = 506.193
W = 0
P = 0.000 
R = -180
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)

# starting cartesian position
X = 277.4
Y = -430
Z = 800
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)

for x in range(2):
    Y = Y+152.4
    pose=[X, Y, Z, W, P, R]
    woody.write_cartesian_position(pose)

    X = X-25
    pose=[X, Y, Z, W, P, R]
    woody.write_cartesian_position(pose)

    Y = Y-152.4
    pose=[X, Y, Z, W, P, R]
    woody.write_cartesian_position(pose)

    X = X-25
    pose=[X, Y, Z, W, P, R]
    woody.write_cartesian_position(pose)

distance = 7
plc.travel(Y_LEFT_MOTION, distance, "inches", speed)
translation_distance += distance
print(f"Current position {translation_distance}")

# starting cartesian position
X = 100
Y = -430
pose=[X, Y, Z, W, P, R]
woody.write_cartesian_position(pose)

# Starting position and layer setup
starting_x = 100
starting_y = -430
starting_z = 800
Z = starting_z
t = 25  # mm layer height (Z decrement)
set_z = woody.set_z_value(0)

for z_position in range(2):
    print(f"Z position {z_position + 1}")

    for layer in range(26):
        print(f"[LAYER] Starting layer {layer + 1}")
        temp_distance = 0

        positions = [
            [starting_x, starting_y],
            [277.4, starting_y],
            [277.4, -405.0],
            [125.0, -405.0],
            [125.0, 0.0]
        ]

        for pos in positions:
            woody.write_cartesian_position([pos[0], pos[1], Z, W, P, R])

        # Translate 176.6 mm
        distance = 176.6
        temp_distance += distance
        translation_distance += distance
        print(f"Translating: {temp_distance} mm, Total: {translation_distance} mm")
        plc.travel(Y_LEFT_MOTION, distance, "mm", speed)

        moves = [
            [277.4, 0.0],
            [277.4, 25.0],
            [125.0, 25.0]
        ]
        for pos in moves:
            woody.write_cartesian_position([pos[0], pos[1], Z, W, P, R])

        # Translate 584.6 mm
        distance = 584.6
        temp_distance += distance
        translation_distance += distance
        print(f"Translating: {temp_distance} mm, Total: {translation_distance} mm")
        plc.travel(Y_LEFT_MOTION, distance, "mm", speed)

        moves = [
            [277.4, 25.0],
            [277.4, 50.0],
            [125.0, 50.0]
        ]
        for pos in moves:
            woody.write_cartesian_position([pos[0], pos[1], Z, W, P, R])

        # Translate 405 mm
        distance = 405.0
        temp_distance += distance
        translation_distance += distance
        print(f"Translating: {temp_distance} mm, Total: {translation_distance} mm")
        plc.travel(Y_LEFT_MOTION, distance, "mm", speed)

        moves = [
            [125.0, 229.6],
            [277.4, 229.6],
            [277.4, 254.6],
            [starting_x, 254.6],
            [starting_x, starting_y]
        ]
        for pos in moves:
            woody.write_cartesian_position([pos[0], pos[1], Z, W, P, R])

        # Reset robot Y-position
        print("Translate robot back Y = 1219.2mm")
        distance = temp_distance
        translation_distance -= distance
        print(f"Returning: {distance} mm, Total: {translation_distance} mm")
        plc.travel(Y_RIGHT_MOTION, distance, "mm", speed)

        # Move Z up for next layer
        Z -= layer_height

    transition_distance += z_transition
    plc.travel(Z_UP_MOTION, transition_distance, "mm", speed)


# turn off green light to show program is done
plc.write_modbus_coils(GREEN,False)