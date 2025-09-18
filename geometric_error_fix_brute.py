# === Imports ===
import sys
import os
import time
import threading
import utils

print("=== Program initialized ===")

# === Parameters ===
speed = 200             # Robot travel speed (mm/s)
print_speed = 200        # Printing speed (mm/s)
inside_offset = 6       # Offset for inner infill moves (mm)
layer_height = 4        # Vertical step per layer (mm)
z_offset = 20           # Safe Z offset for travel moves (mm)
x_offset = 13.5         # X-axis offset (mm)
print_offset = 5        # Vertical offset between passes (mm)
z_correction = 4        # Small correction in Z for alignment (mm)
tolerance = 0
z_increment = layer_height

print("Parameters set.")


# === Helper Function ===
def apply_z_correction(pose, layer_height, tolerance):
    """Check and apply Z correction safely (extruder OFF during adjustment)."""
    corrected_z = utils.z_difference(layer_height, pose[2], tolerance)
    if corrected_z != pose[2]:
        pose[2] = corrected_z
        utils.plc.md_extruder_switch("off")
        utils.woody.write_cartesian_position(pose)  # update robot Z only
        utils.plc.md_extruder_switch("on")
    return pose

# === Optional Machine Vision Mode ===
if len(sys.argv) > 1 and sys.argv[1].lower() in ("mv", "machinevision"):
    utils.open_all_cameras()
    print("Machine vision mode: cameras opened.")
else:
    print("Machine vision mode OFF (no cameras opened).")

# === Robot & PLC Setup ===
utils.woody.set_speed(speed)
utils.woody.set_robot_speed_percent(100)
utils.plc.reset_coils()
time.sleep(2)
print("Robot speed configured and PLC coils reset.")

# === Initial Pose ===
z = 0
pose = [-100, 0, z, 0, 90, 0]
utils.woody.write_cartesian_position(pose)
print(f"Robot moved to initial pose: {pose}")

# === Safe Start ===
utils.plc.md_extruder_switch("off")
print("Extruder OFF for safe start.")

while any(utils.plc.read_modbus_coils(c) for c in (8, 9, 14)):
    print("Safety check: coils active, moving Z down and Y right...")
    for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
        utils.plc.write_modbus_coils(coil, True)

for coil in (utils.Z_DOWN_MOTION, utils.Y_RIGHT_MOTION):
    utils.plc.write_modbus_coils(coil, False)
print("Safety check complete.")
time.sleep(1)


# === Height Calibration ===
pose, z = utils.calibrate_height(pose, layer_height)

temp = z

# === Print Setup ===
z_translation_value = 4 * layer_height

height_accumulation = 0
flg = True

utils.plc.md_extruder_switch("on")
print("Extruder ON, starting print sequence...")
time.sleep(5)

# === Printing Loop ===
while flg:
    layers = 1
    print(f"\n=== Starting new layer at z = {z:.2f} mm ===")

    # --- Move to Start Pose ---
    pose = [-100, 0, z, 0, 90, 0]
    utils.woody.write_cartesian_position(pose)
    print(f"Moved to start pose: {pose}")
    pose = apply_z_correction(pose, layer_height, tolerance)
    print(f"Z is{z}")

    # --- Perimeter Path ---
    utils.woody.set_speed(print_speed)
    utils.plc.md_extruder_switch("on")
    print("Extruder ON for perimeter path.")
    print(f"Z is{z}")

    # Path 1: X move
    pose[0] = -60
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along X: {pose}")
    pose = apply_z_correction(pose, layer_height, tolerance)
    print(f"Z is{z}")

    # Path 2: Y forward
    pose[1] = 400
    utils.woody.write_cartesian_position(pose)
    print(f"Moving along Y forward: {pose}")
    pose = apply_z_correction(pose, layer_height, tolerance)
    print(f"Z is{z}")

#     # Path 2: Y forward
#     pose[0] = 100
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
#     print(f"Z is{z}")


#     pose[1] = 0
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
#     print(f"Z is{z}")

#     utils.plc.md_extruder_switch("off")


#     utils.woody.set_speed(speed)
#     pose[2] += 20
#     utils.woody.write_cartesian_position(pose)

#     print(f"Moving along Y forward: {pose}")

#     utils.plc.travel(utils.Y_LEFT_MOTION, 400, 'mm', 'y')  # Travel right
    
#     # pose = apply_z_correction(pose, layer_height, tolerance)
    
    
#     pose[1] = 400
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)

#     utils.plc.md_extruder_switch("on")
#     utils.woody.set_speed(print_speed)

#     pose[1] = -400
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
   

#     pose[0] = -60
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)


#     pose[1] = 400
#     utils.woody.write_cartesian_position(pose)
#     print(f"Moving along Y forward: {pose}")
#     pose = apply_z_correction(pose, layer_height, tolerance)
#     utils.plc.md_extruder_switch("off")

    flg = False

    # # Path 3: X forward
    # pose[0] = 100
    # utils.woody.write_cartesian_position(pose)
    # print(f"Moving along X forward: {pose}")
    # pose = apply_z_correction(pose, layer_height, tolerance)
    # print(f"Z is{z}")

    # # Path 4+: Y back in steps
    # for y in [200]:#, 150, 100, 50, 0]:
    #     pose[1] = y
    #     utils.woody.write_cartesian_position(pose)
    #     print(f"Moving along Y back: {pose}")
    #     pose = apply_z_correction(pose, layer_height, tolerance)
    #     print(f"Z is{z}")

    # # End after one loop (debug mode)
    # utils.plc.md_extruder_switch("off")

    # # === Increment Z and update layer height ===
    # z += z_increment        # fixed increment
    # layer_height += 4       # increase layer_height by 4 each loop
    # layers += 1

    # # stop when z exceeds 12 mm
    # if abs(z-temp) > 8:
    #     print(z-temp)
    #     flg = False




#     # --- Travel Move (Lift + Y-shift) ---
#     utils.plc.md_extruder_switch("off")
#     utils.woody.set_speed(speed)
#     pose[2] += 20
#     pose[1] = 250
#     utils.woody.write_cartesian_position(pose)
#     print(f"Traveling to Y-left prep: {pose}")

#     distance = 50
#     utils.plc.travel(Y_LEFT_MOTION, distance, "mm", "y")
#     print(f"Traveling Y-left {distance}mm.")
#     time.sleep(2)

#     # --- Lower Back to Print Height ---
#     pose[2] -= 20
#     utils.woody.write_cartesian_position(pose)
#     print(f"Lowered back to print Z: {pose[2]}")

#     # --- Return Paths ---
#     utils.woody.set_speed(print_speed)
#     utils.plc.md_extruder_switch("on")
#     time.sleep(2)
#     pose[1] = -175
#     utils.woody.write_cartesian_position(pose)
#     # utils.monitor_distance_sensor(layer_height, True)
#     print(f"Return path Y=0: {pose}")

#     pose[0] = -60
#     utils.woody.write_cartesian_position(pose)
#     # utils.monitor_distance_sensor(layer_height, True)
#     print(f"Return path X back: {pose}")

#     pose[1] = 250
#     utils.woody.write_cartesian_position(pose)
#     print(f"Return path final Y forward: {pose}")
#     # utils.monitor_distance_sensor(layer_height, True)
#     time.sleep(2)
#     utils.woody.set_speed(speed)
#     utils.plc.md_extruder_switch("off")

#     # --- Increment Z for Next Layer ---
#     z += layer_height
#     pose = [-100, 0, z, 0, 90, 0]
#     utils.woody.write_cartesian_position(pose)
#     print(f"Incremented Z by {layer_height}. New z = {z}")

#     # --- Travel Back ---
#     print("Travel back")
#     utils.plc.travel(Y_RIGHT_MOTION, distance, "mm", "y")



# print("=== Print job complete ===")
