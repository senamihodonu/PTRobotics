import cv2
import cv2.aruco as aruco
import os

# === Parameters ===
aruco_dict_type = aruco.DICT_6X6_250   # Type of dictionary
marker_size = 700                      # Size of each marker in pixels
num_markers = 10                       # Number of markers to generate
output_folder = "aruco_markers"        # Folder to save markers

# === Create output folder if it doesn't exist ===
os.makedirs(output_folder, exist_ok=True)

# === Get the ArUco dictionary ===
aruco_dict = aruco.getPredefinedDictionary(aruco_dict_type)

# === Generate, save, and preview markers ===
for marker_id in range(num_markers):
    marker_image = aruco.generateImageMarker(aruco_dict, marker_id, marker_size)

    file_path = os.path.join(output_folder, f"aruco_marker_{marker_id}.png")
    cv2.imwrite(file_path, marker_image)
    print(f"Saved marker ID {marker_id} at {file_path}")

    # Preview marker
    cv2.imshow("ArUco Marker", marker_image)
    print("Press any key to continue...")
    cv2.waitKey(0)  # Wait for key press before moving to next marker
    cv2.destroyAllWindows()

print("All markers generated and previewed successfully.")
import cv2
import cv2.aruco as aruco
print(cv2.__version__)
print(hasattr(aruco, "drawMarker"))
