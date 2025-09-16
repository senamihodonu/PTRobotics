import cv2
import cv2.aruco as aruco
import os
import numpy as np

# === Parameters ===
aruco_dict_type = aruco.DICT_6X6_250   # Type of dictionary
marker_size = 300                      # Size of each marker in pixels
num_markers = 10                       # Number of markers to generate
border_size = 50                       # Border thickness in pixels
output_folder = "aruco_markers"        # Folder to save markers

# === Create output folder if it doesn't exist ===
os.makedirs(output_folder, exist_ok=True)

# === Get the ArUco dictionary ===
aruco_dict = aruco.getPredefinedDictionary(aruco_dict_type)

# === Generate, save, and preview markers ===
for marker_id in range(num_markers):
    marker_image = aruco.generateImageMarker(aruco_dict, marker_id, marker_size)

    # Add white border around the marker
    bordered_marker = cv2.copyMakeBorder(
        marker_image,
        border_size, border_size, border_size, border_size,  # top, bottom, left, right
        cv2.BORDER_CONSTANT,
        value=255  # White border
    )

    file_path = os.path.join(output_folder, f"aruco_marker_{marker_id}.png")
    cv2.imwrite(file_path, bordered_marker)
    print(f"Saved marker ID {marker_id} with border at {file_path}")

    # Preview marker
    cv2.imshow("ArUco Marker", bordered_marker)
    print("Press any key to continue...")
    cv2.waitKey(0)  # Wait for key press before moving to next marker
    cv2.destroyAllWindows()

print("All markers generated with borders and previewed successfully.")
