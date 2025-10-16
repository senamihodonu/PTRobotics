import cv2
import argparse
import time
import os

# Map dictionary name to OpenCV enum
ARUCO_DICTS = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
    "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
    "DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
    "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
    "DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
    "DICT_7X7_50": cv2.aruco.DICT_7X7_50,
    "DICT_7X7_100": cv2.aruco.DICT_7X7_100,
    "DICT_7X7_250": cv2.aruco.DICT_7X7_250,
    "DICT_7X7_1000": cv2.aruco.DICT_7X7_1000,
    "DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
}


def generate_aruco(dictionary_id, marker_id, size, output_file):
    # Load the dictionary
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_id)

    # Generate marker
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size)

    # Add timestamp to filename
    base, ext = os.path.splitext(output_file)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_file_with_timestamp = f"{base}_{timestamp}{ext}"

    # Save marker
    cv2.imwrite(output_file_with_timestamp, marker_img)
    print(f"✅ Saved marker ID {marker_id} from {dictionary_id} to {output_file_with_timestamp}")

    # Show marker
    cv2.imshow("ArUco Marker", marker_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ArUco marker images")
    parser.add_argument("--dict", type=str, default="DICT_4X4_50",
                        help="Dictionary name (e.g. DICT_4X4_50, DICT_5X5_100, DICT_6X6_250, DICT_7X7_1000)")
    parser.add_argument("--id", type=int, default=0, help="Marker ID to generate")
    parser.add_argument("--size", type=int, default=300, help="Size of marker image (pixels)")
    parser.add_argument("--out", type=str, default="aruco_marker.png", help="Output file name")
    args = parser.parse_args()

    if args.dict not in ARUCO_DICTS:
        print(f"❌ Unknown dictionary {args.dict}")
        print("Available:", ", ".join(ARUCO_DICTS.keys()))
    else:
        generate_aruco(ARUCO_DICTS[args.dict], args.id, args.size, args.out)

