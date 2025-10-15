import cv2
import numpy as np
import argparse

# === ArUco setup ===
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
aruco_params = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

# === Real marker size in mm ===
MARKER_SIZE_MM = 50  # Set to your actual ArUco marker size


def detect_and_draw(frame):
    """Detect ArUco markers, draw measurements, and return distance dictionary."""
    h, w = frame.shape[:2]
    frame_center = (w // 2, h // 2)

    # Draw frame center
    cv2.circle(frame, frame_center, 6, (255, 0, 0), -1)
    cv2.putText(frame, "Center", (frame_center[0] + 10, frame_center[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    corners, ids, _ = detector.detectMarkers(frame)
    distances_dict = {}

    if ids is not None:
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        # Estimate pixel/mm scale using the first marker
        c0 = corners[0].reshape((4, 2))
        width_px = np.linalg.norm(c0[0] - c0[1])
        px_per_mm = width_px / MARKER_SIZE_MM

        for c, i in zip(corners, ids.flatten()):
            c = c.reshape((4, 2))
            cx, cy = int(c[:, 0].mean()), int(c[:, 1].mean())

            # Draw marker center
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            # Distance from frame center
            dx, dy = cx - frame_center[0], cy - frame_center[1]
            distance_center_px = np.sqrt(dx ** 2 + dy ** 2)
            distance_center_mm = distance_center_px / px_per_mm

            # Distances to edges
            dist_left_px, dist_right_px = cx, w - cx
            dist_top_px, dist_bottom_px = cy, h - cy

            dist_left_mm = dist_left_px / px_per_mm
            dist_right_mm = dist_right_px / px_per_mm
            dist_top_mm = dist_top_px / px_per_mm
            dist_bottom_mm = dist_bottom_px / px_per_mm

            # Draw measurements
            cv2.line(frame, (cx, cy), (0, cy), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_left_mm:.1f}mm", (cx // 2, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            cv2.line(frame, (cx, cy), (w, cy), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_right_mm:.1f}mm", ((cx + w) // 2, cy - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            cv2.line(frame, (cx, cy), (cx, 0), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_top_mm:.1f}mm", (cx + 5, cy // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            cv2.line(frame, (cx, cy), (cx, h), (255, 255, 0), 1)
            cv2.putText(frame, f"{dist_bottom_mm:.1f}mm", (cx + 5, (cy + h) // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

            cv2.line(frame, frame_center, (cx, cy), (0, 255, 255), 2)
            cv2.putText(frame, f"{distance_center_mm:.1f}mm",
                        ((cx + frame_center[0]) // 2 + 5, (cy + frame_center[1]) // 2 + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            cv2.putText(frame, f"ID:{i}", (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Add to dictionary
            distances_dict[int(i)] = {
                "center_mm": round(distance_center_mm, 2),
                "left_mm": round(dist_left_mm, 2),
                "right_mm": round(dist_right_mm, 2),
                "top_mm": round(dist_top_mm, 2),
                "bottom_mm": round(dist_bottom_mm, 2),
                "center_px": round(distance_center_px, 2),
            }

    return frame, distances_dict


def detect_from_image(path, save_marked=True, return_marked=False):
    """
    Detect ArUco markers in the given image, draw annotations, and optionally
    save and/or return the marked image.

    Args:
        path (str): Path to the input image.
        save_marked (bool): Whether to save the marked image to disk. Default: True.
        return_marked (bool): Whether to return the marked image array. Default: False.

    Returns:
        dict or (dict, np.ndarray): distances, or (distances, marked_image) if return_marked=True
    """
    import cv2
    import os

    img = cv2.imread(path)
    if img is None:
        print(f"❌ Could not read image: {path}")
        return {} if not return_marked else ({}, None)

    # --- Perform detection and get annotated image + distances
    result, distances = detect_and_draw(img)

    # --- Display results
    cv2.imshow("ArUco Detection", result)
    print("📏 Measured distances (mm):")

    for marker_id, data in distances.items():
        print(f"Marker ID: {marker_id}")
        for key, value in data.items():
            print(f"  {key:10}: {float(value):.2f} mm")

    # --- Save marked image
    if save_marked:
        folder, filename = os.path.split(path)
        name, ext = os.path.splitext(filename)
        marked_path = os.path.join(folder, f"{name}_marked{ext}")
        cv2.imwrite(marked_path, result)
        print(f"🖍️ Marked image saved to: {marked_path}")

    # --- Cleanup
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # --- Return according to requested mode
    if return_marked:
        return distances, result
    else:
        return distances




if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="ArUco marker detection")
    # parser.add_argument("--image", type=str, required=True, help="Path to an image with ArUco markers")
    # args = parser.parse_args()
    image  = "c1_20250917-152359.jpg"
    # detect_from_image(args.image)
    print(detect_from_image(image))
