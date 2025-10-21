import os
import sys
import time
import cv2
import numpy as np
import argparse

# --- Ensure UTF-8 output for Windows terminals ---
sys.stdout.reconfigure(encoding='utf-8')

# === ArUco setup ===
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
ARUCO_PARAMS = cv2.aruco.DetectorParameters()
DETECTOR = cv2.aruco.ArucoDetector(ARUCO_DICT, ARUCO_PARAMS)

# === Marker properties ===
MARKER_SIZE_MM = 50  # Actual ArUco marker size in millimeters


def measure_marker_to_marker_distance(frame, corners, ids, px_per_mm):
    """
    Compute and visualize distances and angles between each pair of detected markers.
    Marker-to-marker line: yellow, text: black.
    """
    distances = {}
    centers = []

    # Compute marker centers
    for c, marker_id in zip(corners, ids.flatten()):
        pts = c.reshape((4, 2))
        cx, cy = int(pts[:, 0].mean()), int(pts[:, 1].mean())
        centers.append((marker_id, (cx, cy)))

    # Compute all pairwise distances and angles
    for i in range(len(centers)):
        id1, (x1, y1) = centers[i]
        for j in range(i + 1, len(centers)):
            id2, (x2, y2) = centers[j]

            dist_px = np.hypot(x2 - x1, y2 - y1)
            dist_mm = dist_px / px_per_mm

            # Calculate angle in degrees (relative to horizontal axis)
            angle_rad = np.arctan2(y2 - y1, x2 - x1)
            angle_deg = np.degrees(angle_rad)

            distances[(int(id1), int(id2))] = {
                "pixels": round(dist_px, 2),
                "millimeters": round(dist_mm, 2),
                "angle_deg": round(angle_deg, 2)
            }

            # Draw connecting line (yellow)
            mid_x, mid_y = int((x1 + x2) / 2), int((y1 + y2) / 2)
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 255), 2, lineType=cv2.LINE_AA)

            # Draw text showing distance and angle
            cv2.putText(frame, f"{dist_mm:.1f}mm {angle_deg:.1f}°",
                        (mid_x + 5, mid_y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, lineType=cv2.LINE_AA)

    return distances


def detect_and_draw(frame, measure_between_markers=False):
    """
    Detect ArUco markers in the frame, draw annotations, and return distance data.
    If measure_between_markers=True, measure distances between marker centers instead of to frame edges.
    """
    h, w = frame.shape[:2]
    frame_center = (w // 2, h // 2)

    # Draw frame center point
    cv2.circle(frame, frame_center, 6, (255, 0, 0), -1)
    cv2.putText(frame, "Center", (frame_center[0] + 10, frame_center[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    corners, ids, _ = DETECTOR.detectMarkers(frame)
    distances_dict = {}

    if ids is not None:
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        # Estimate pixel-to-mm scale from the first marker
        first_marker = corners[0].reshape((4, 2))
        width_px = np.linalg.norm(first_marker[0] - first_marker[1])
        px_per_mm = width_px / MARKER_SIZE_MM

        if measure_between_markers:
            # Measure distances between centers of markers
            distances_dict = measure_marker_to_marker_distance(frame, corners, ids, px_per_mm)
        else:
            # Measure distances from each marker to frame sides
            for c, marker_id in zip(corners, ids.flatten()):
                c = c.reshape((4, 2))
                cx, cy = int(c[:, 0].mean()), int(c[:, 1].mean())

                # Draw marker center
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

                # Distances (px and mm)
                dx, dy = cx - frame_center[0], cy - frame_center[1]
                dist_center_px = np.hypot(dx, dy)

                dist_center_mm = dist_center_px / px_per_mm
                dist_left_mm = cx / px_per_mm
                dist_right_mm = (w - cx) / px_per_mm
                dist_top_mm = cy / px_per_mm
                dist_bottom_mm = (h - cy) / px_per_mm

                # Draw helper lines + text
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

                # Draw center line (yellow) and distance text (black)
                cv2.line(frame, frame_center, (cx, cy), (0, 255, 255), 2)
                cv2.putText(frame, f"{dist_center_mm:.1f}mm",
                            ((cx + frame_center[0]) // 2 + 5, (cy + frame_center[1]) // 2 + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, lineType=cv2.LINE_AA)

                # Label marker
                cv2.putText(frame, f"ID:{marker_id}", (cx + 10, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Store data
                distances_dict[int(marker_id)] = {
                    "center_mm": round(dist_center_mm, 2),
                    "left_mm": round(dist_left_mm, 2),
                    "right_mm": round(dist_right_mm, 2),
                    "top_mm": round(dist_top_mm, 2),
                    "bottom_mm": round(dist_bottom_mm, 2),
                    "center_px": round(dist_center_px, 2),
                }

    return frame, distances_dict


def detect_from_image(path, save_marked=True, return_marked=False, show=False, measure=False):
    """
    Detect ArUco markers in an image, annotate results, and return measurements.
    """
    abs_path = os.path.abspath(path)
    print(f"🔍 Reading image: {abs_path}")
    offset = 0

    img = cv2.imread(abs_path)
    if img is None:
        print(f"[ERROR] Could not read image: {abs_path}")
        return ({}, None) if return_marked else {}

    annotated, distances = detect_and_draw(img, measure_between_markers=measure)

    if measure:
        print("\n📐 Marker-to-Marker Distances and Angles:")
        for (id1, id2), dist in distances.items():
            print(f"  Between {id1} ↔ {id2}: {dist['millimeters']:.2f} mm, "
                  f"Angle: {dist['angle_deg']:.2f}°")
            offset = dist['millimeters']
    else:
        print("\n📏 Measured distances (marker-to-frame in mm):")
        for marker_id, data in distances.items():
            print(f"Marker ID: {marker_id}")
            for key, value in data.items():
                print(f"  {key:10}: {float(value):.2f} mm")

    # Save annotated image
    if save_marked:
        folder, filename = os.path.split(abs_path)
        name, ext = os.path.splitext(filename)
        marked_path = os.path.join(folder, f"{name}_marked{ext}")
        cv2.imwrite(marked_path, annotated)
        print(f"\n🖍️ Marked image saved to: {marked_path}")

    # Display window if requested
    if show:
        cv2.imshow("ArUco Detection", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    return (offset, annotated) if return_marked else offset


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Detect ArUco markers and measure distances and angles (in mm & degrees)."
    )
    parser.add_argument("--image", required=True, help="Path to input image file.")
    parser.add_argument("--show", action="store_true", help="Display image window.")
    parser.add_argument("--nosave", action="store_true", help="Do not save marked image.")
    parser.add_argument("--returnimg", action="store_true", help="Return annotated image array.")
    parser.add_argument("--measure", action="store_true",
                        help="Measure distances between marker centers instead of to frame edges.")
    args = parser.parse_args()

    distance = detect_from_image(
        path=args.image,
        save_marked=not args.nosave,
        return_marked=args.returnimg,
        show=args.show,
        measure=args.measure
    )
    print(distance)


if __name__ == "__main__":
    main()
