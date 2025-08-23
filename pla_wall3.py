# === Imports ===
import sys
import os
import time
import threading

# === Path setup ===
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.normpath(os.path.join(current_dir, "fanuc_ethernet_ip_drivers", "src"))
sys.path.append(src_path)

# === Custom libraries ===
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

print("Small program established")

# === Initialize PLC and robot ===
plc = PyPLCConnection(PLC_IP)
woody = robot(ROBOT_IP)

# === Parameters ===
speed = 200
print_speed = 200
offset = 4
layer_height = 4
z_offset = 20
n=1 

# === Configure robot/PLC ===
woody.set_speed(speed)
woody.set_robot_speed_percent(100)
plc.reset_coils()
time.sleep(2)

# === Initial pose ===
pose = [-100, 0, 0, 0, 90, 0]  # X, Y, Z, W, P, R
woody.write_cartesian_position(pose)

# === Safe start: move Z down + Y right until coils 8, 9, or 14 deactivate ===
plc.md_extruder_switch("off")
while any(plc.read_modbus_coils(c) for c in (8, 9, 14)):
    for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
        plc.write_modbus_coils(coil, True)

# Stop motion
for coil in (Z_DOWN_MOTION, Y_RIGHT_MOTION):
    plc.write_modbus_coils(coil, False)
time.sleep(1)

# === Print setup ===
woody.set_speed(print_speed)
plc.md_extruder_switch("on")
time.sleep(1)

# === Lead Sequence: Pass 1 ===
z = 0
for layer in range(n):
    
    # --- First extrusion path ---
    plc.md_extruder_switch("on")
    woody.set_speed(print_speed)  

    pose = [-100, -90, z, 0, 90, 0]   # Start point
    woody.write_cartesian_position(pose)

    pose[0] = -60                     # Move in X
    woody.write_cartesian_position(pose)

    pose[1] = 80                      # Move in Y
    woody.write_cartesian_position(pose)

    pose[0] = 260                     # Move in X
    woody.write_cartesian_position(pose)

    pose[1] = -80                     # Move in Y
    woody.write_cartesian_position(pose)

    pose[0] = 100                     # Move in X
    woody.write_cartesian_position(pose)

    # --- Pause extrusion / reposition ---
    plc.md_extruder_switch("off")
    woody.set_speed(speed)
    pose[2] += z_offset                # Lift Z temporarily
    woody.write_cartesian_position(pose)

    pose[0] = -60 + offset
    pose[1] = -80 + offset
    woody.write_cartesian_position(pose)

    pose[2] -= z_offset                # Lift Z temporarily
    woody.write_cartesian_position(pose)

    
    # --- Second extrusion path (offset) ---
    plc.md_extruder_switch("on")
    woody.set_speed(print_speed)

    pose[0] = 100 - offset
    pose[1] = 80 - offset
    woody.write_cartesian_position(pose)

    pose[0] = 260 - offset
    pose[1] = -80 + offset
    woody.write_cartesian_position(pose)

    # --- Pause extrusion / travel ---
    plc.md_extruder_switch("off") 
    woody.set_speed(speed)
    z += 20                           # Raise Z
    pose = [-100, 0, z, 0, 90, 0]
    woody.write_cartesian_position(pose)

    plc.travel(Y_LEFT_MOTION, 470, 'mm', 'y')  # Travel left

    # --- Third extrusion path (return) ---
    plc.md_extruder_switch("on") 
    z -= 20
    pose = [100, 405, z, 0, 90, 0]
    woody.write_cartesian_position(pose)
    woody.set_speed(print_speed)

    pose[1] = -400
    woody.write_cartesian_position(pose)

    pose[0] = -60
    woody.write_cartesian_position(pose)

    pose[1] = 400
    woody.write_cartesian_position(pose)

    # --- Pause extrusion / offset path ---
    plc.md_extruder_switch("off") 
    woody.set_speed(speed)
    pose[2] += 20                     # Raise Z
    woody.write_cartesian_position(pose)

    pose[0] = 100 - offset
    pose[1] = 400 - offset
    woody.write_cartesian_position(pose)

    pose[2] -= 20                     # Lower Z
    woody.write_cartesian_position(pose)

    plc.md_extruder_switch('on')         # Resume extrusion
    woody.set_speed(print_speed)

    pose[0] = -60 + offset
    pose[1] = 202
    woody.write_cartesian_position(pose)

    pose[0] = 100 - offset
    pose[1] = 0
    woody.write_cartesian_position(pose)

    pose[0] = -60 + offset
    pose[1] = -202
    woody.write_cartesian_position(pose)

    pose[0] = 100 - offset
    pose[1] = -400 + offset
    woody.write_cartesian_position(pose)

    # --- End of layer ---
    plc.md_extruder_switch("off") 
    z += z_offset
    woody.set_speed(speed)
    pose = [-100, 0, z, 0, 90, 0]
    woody.write_cartesian_position(pose)

    z -= z_offset
    plc.travel(Y_RIGHT_MOTION, 470, 'mm', 'y')  # Travel right

    z += layer_height                # Increment Z for next layer


# === Z-axis reposition before Pass 2 ===
z_translation = woody.read_current_cartesian_pose()[2] + layer_height - z_offset
plc.travel(Z_UP_MOTION, z_translation, 'mm', 'z')

z= 0
for layer in range(n):
    
    # Start extrusion
    plc.md_extruder_switch("on")
    woody.set_speed(print_speed)  

    # Initial pose
    pose = [-100, -90, z, 0, 90, 0]  # X, Y, Z, W, P, R
    woody.write_cartesian_position(pose)

    # Print path (rectangular pattern)
    pose[0] = -60        # Move X
    woody.write_cartesian_position(pose)

    pose[1] = 80         # Move Y
    woody.write_cartesian_position(pose)

    pose[0] = 260        # Move X
    woody.write_cartesian_position(pose)

    pose[1] = -80        # Move Y
    woody.write_cartesian_position(pose)

    pose[0] = 100        # Move X
    woody.write_cartesian_position(pose)

    plc.md_extruder_switch("off")
    woody.set_speed(speed)
    pose[2] += z_offset
    woody.write_cartesian_position(pose)

    pose[0] = -60+offset        # Move X
    pose[1] = -80+offset        # Move X
    woody.write_cartesian_position(pose)

    pose[2] -= z_offset
    woody.write_cartesian_position(pose)
    
    plc.md_extruder_switch("on")
    woody.set_speed(print_speed)

    pose[0] = 100-offset        # Move X
    pose[1] = 80-offset        # Move X
    woody.write_cartesian_position(pose)

    pose[0] = 260-offset        # Move X
    pose[1] = -80+offset        # Move X
    woody.write_cartesian_position(pose)

    # Pause extrusion and raise Z
    plc.md_extruder_switch("off") 
    woody.set_speed(speed)
    z += 20
    pose = [-100, 0, z, 0, 90, 0]
    woody.write_cartesian_position(pose)

    # Travel Y left before next pass
    plc.travel(Y_LEFT_MOTION, 470, 'mm', 'y')

    # Resume extrusion
    plc.md_extruder_switch("on") 
    z -= 20
    pose = [100, 405, z, 0, 90, 0]
    woody.write_cartesian_position(pose)
    woody.set_speed(print_speed)

    # Print return path
    pose[1] = -400       # Move Y
    woody.write_cartesian_position(pose)

    pose[0] = -60        # Move X
    woody.write_cartesian_position(pose)

    pose[1] = 400        # Move Y
    woody.write_cartesian_position(pose)
    plc.md_extruder_switch("off") 
    woody.set_speed(speed)
    pose[2]+=20
    woody.write_cartesian_position(pose)

    pose[0] = 100-offset        # Move X
    pose[1] = 400-offset        # Move X
    woody.write_cartesian_position(pose)

    pose[2]-=20
    woody.write_cartesian_position(pose)
    plc.md_extruder_switch("on") 
    woody.set_speed(print_speed)

    pose[0] = -60+offset        # Move X
    pose[1] = 202        # Move X
    woody.write_cartesian_position(pose)

    pose[0] = 100-offset        # Move X
    pose[1] = 0        # Move X
    woody.write_cartesian_position(pose)

    pose[0] = -60+offset        # Move X
    pose[1] = -202        # Move X
    woody.write_cartesian_position(pose)

    pose[0] = 100-offset        # Move X
    pose[1] = -400+offset        # Move X
    woody.write_cartesian_position(pose)

    # End layer, raise Z
    plc.md_extruder_switch("off") 
    z += 20
    woody.set_speed(speed)
    pose = [-100, 0, z, 0, 90, 0]
    woody.write_cartesian_position(pose)

    # Travel Y right before next loop
    z -= 20
    plc.travel(Y_RIGHT_MOTION, 470, 'mm', 'y')

    # Increment Z for next layer
    z += layer_height



