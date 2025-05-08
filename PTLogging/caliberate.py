import cv2
import json
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

# -------- Calibration Helpers --------
def capture_reference_image():
    cap = cv2.VideoCapture(1)  # Change index if needed
    if not cap.isOpened():
        messagebox.showerror("Camera Error", "Could not open camera.")
        return None

    messagebox.showinfo("Info", "Press 'C' to capture image with reference object, 'Q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Calibration - Press 'C' to Capture", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):
            filename = f"calibration_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            cap.release()
            cv2.destroyAllWindows()
            return filename
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return None

def calibrate_pixels_per_mm(image_path, known_width_mm=76):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 500]

    if not contours:
        messagebox.showerror("Error", "No valid contours found.")
        return None

    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    pixels_per_mm = w / known_width_mm

    # Save annotated image
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 3)
    cv2.putText(image, f"{pixels_per_mm:.2f} px/mm", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    output_img = "calibration_result.jpg"
    cv2.imwrite(output_img, image)
    cv2.imshow("Calibration Result", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return pixels_per_mm

def save_calibration(pixels_per_mm, filename="calibration.json"):
    data = {
        "pixels_per_mm": pixels_per_mm,
        "timestamp": datetime.now().isoformat()
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def load_calibration(filename="calibration.json"):
    try:
        with open(filename, 'r') as f:
            return json.load(f)["pixels_per_mm"]
    except:
        return None

# -------- GUI --------
def run_calibration():
    img_path = capture_reference_image()
    if img_path:
        ppm = calibrate_pixels_per_mm(img_path)
        if ppm:
            save_calibration(ppm)
            messagebox.showinfo("Success", f"Calibration saved.\nPixels per mm: {ppm:.2f}")
        else:
            messagebox.showerror("Error", "Calibration failed.")
    else:
        messagebox.showwarning("Cancelled", "No image captured.")

def create_gui():
    root = tk.Tk()
    root.title("Camera Calibration Tool")
    root.geometry("400x200")

    tk.Label(root, text="Camera Calibration & Measurement", font=("Arial", 14)).pack(pady=10)

    tk.Button(root, text="Calibrate Camera", font=("Arial", 12), command=run_calibration).pack(pady=10)

    tk.Button(root, text="Quit", font=("Arial", 12), command=root.destroy).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
