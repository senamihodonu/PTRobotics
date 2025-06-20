import socket
import time
import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import database_manager as db
import csv

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

root = tk.Tk()
root.title("Camera Monitoring and Data Capture")

custom_prefix_var = tk.StringVar(value="Session")
folder_path_var = tk.StringVar(value=os.getcwd())
capture_interval_var = tk.StringVar(value="10")
countdown_var = tk.StringVar(value="")
connection_status_var = tk.StringVar(value="Disconnected")

CAMERA_URLS = [
    "http://172.29.149.105:8080/video",
    "http://172.29.179.38:8080/video"
]

caps = [cv2.VideoCapture(url) for url in CAMERA_URLS]
caps = [cap if cap.isOpened() else None for cap in caps]

SERVER_IP = '172.29.143.185'
SERVER_PORT = 5001
client = None
socket_connected = False

temperature = None
humidity = None
photo_count = 0
collecting_data = False
session_folder = None
session_start_time = None
countdown_seconds = 0
width = None
pressure = None

def update_connection_indicator(connected):
    if connected:
        connection_status_var.set("Connected")
        status_label.config(bg="green")
    else:
        connection_status_var.set("Disconnected")
        status_label.config(bg="red")

def try_connect():
    global socket_connected, client
    if socket_connected:
        return
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        client.connect((SERVER_IP , SERVER_PORT))
        log("Connected to server")
        socket_connected = True
        update_connection_indicator(True)
        fetch_sensor_data()
    except Exception as e:
        log(f"Server not reachable. ({e})")
        if client:
            client.close()
        client = None
        socket_connected = False
        update_connection_indicator(False)

def fetch_sensor_data():
    global temperature, humidity, socket_connected, client, width, pressure
    if socket_connected and client is not None:
        try:
            client.sendall("hello".encode())
            response = client.recv(1024).decode("utf-8")
            log(f"Received from server: {response}")
            try:
                parts = response.split(", ")
                temperature = float(parts[0].split(": ")[1].replace("\u00b0C", ""))
                humidity = float(parts[1].split(": ")[1].replace("%", ""))
                width = float(parts[2].split(": ")[1]) if len(parts) > 2 else None
                pressure = float(parts[3].split(": ")[1]) if len(parts) > 3 else None
            except (IndexError, ValueError) as e:
                log(f"Error parsing sensor data: {e}")
        except Exception as e:
            log(f"Lost connection to server: {e}")
            socket_connected = False
            if client:
                client.close()
            client = None
            update_connection_indicator(False)
    else:
        log("No connection to server. Skipping sensor data.")
        update_connection_indicator(False)

def create_session_folder():
    global session_folder, session_start_time
    session_start_time = time.strftime("%Y%m%d-%H%M%S")
    custom_prefix = custom_prefix_var.get().strip()
    base_folder = folder_path_var.get().strip()
    if not os.path.isdir(base_folder):
        log("Invalid folder path. Please select a valid directory.")
        return
    session_folder = os.path.join(base_folder, f"{custom_prefix}_{session_start_time}")
    os.makedirs(session_folder, exist_ok=True)
    log(f"Session folder created at: {session_folder}")

def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_path_var.set(folder)

def capture_and_save():
    global temperature, humidity, photo_count, socket_connected, session_folder, session_start_time
    if not session_folder:
        create_session_folder()

    fetch_sensor_data()
    rets, frames = zip(*[(cap.read() if cap else (False, None)) for cap in caps])
    if not any(rets):
        log("Error: No cameras available for capture.")
        return

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    photo_count += 1
    print_tag = f"{timestamp}_p{photo_count}"

    try:
        print_speed = float(print_speed_var.get())
        layer_height = float(layer_height_var.get())
        extruder = extruder_var.get()
    except ValueError:
        log("Invalid input! Using defaults (print_speed=50, layer_height=0.2).")
        print_speed, layer_height, extruder = 50.0, 0.2, "SSE"

    group_tag = f"{custom_prefix_var.get()}_{session_start_time}_{extruder}"

    overlay_lines = [
        f"Tag: {print_tag}",
        f"Temp: {temperature:.1f} deg C" if temperature is not None else "Temp: N/A",
        f"Humidity: {humidity:.1f}%" if humidity is not None else "Humidity: N/A",
        f"Extruder: {extruder}"
    ]

    image_tags = []
    for idx, (ret, frame) in enumerate(zip(rets, frames)):
        if ret:
            image_name = f"c{idx+1}_{timestamp}.jpg"
            image_path = os.path.join(session_folder, image_name)

            for i, line in enumerate(overlay_lines):
                y_pos = frame.shape[0] - 10 - i * 25
                cv2.putText(
                    frame,
                    line,
                    (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA
                )

            cv2.imwrite(image_path, frame)
            image_tags.append(image_name)
        else:
            image_tags.append(None)

    db.insert_print_data(
        group_tag, print_tag, *image_tags,
        humidity, temperature, print_speed,
        layer_height, width, pressure
    )

    log(f"Data saved: {print_tag}, Temp: {temperature}, Humidity: {humidity}, Width: {width}, Pressure: {pressure}, Group: {group_tag}")

def update_video():
    frames = []
    for cap in caps:
        if cap:
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (240, 180))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(ImageTk.PhotoImage(Image.fromarray(frame)))
            else:
                frames.append(None)
        else:
            frames.append(None)
    for label, frame in zip(video_labels, frames):
        if frame:
            label.config(image=frame)
            label.image = frame
    root.after(30, update_video)

def toggle_auto_capture():
    global collecting_data
    collecting_data = not collecting_data
    if collecting_data:
        auto_capture()
        update_countdown()

def auto_capture():
    global countdown_seconds
    if not collecting_data:
        return
    try:
        interval = float(capture_interval_var.get())
        if interval <= 0:
            raise ValueError
    except ValueError:
        log("Invalid interval. Defaulting to 10 seconds.")
        interval = 10.0
    capture_and_save()
    countdown_seconds = int(interval)
    root.after(int(interval * 1000), auto_capture)

def update_countdown():
    global countdown_seconds
    if not collecting_data:
        countdown_var.set("")
        return
    countdown_var.set(f"Next capture in: {countdown_seconds}s")
    countdown_seconds -= 1
    root.after(1000, update_countdown)

def quit_program():
    log("Quitting application — exporting session data if available.")
    try:
        export_session_data()
    except Exception as e:
        log(f"Error during export on quit: {e}")

    for cap in caps:
        if cap:
            cap.release()
    if client:
        try:
            client.close()
        except Exception:
            pass
    root.quit()
    log("Resources released. Goodbye!")

def export_session_data():
    if not session_folder or not session_start_time:
        log("No session data to export — capture session hasn't started.")
        return
    try:
        extruder = extruder_var.get()
    except Exception:
        extruder = "Unknown"
    group_tag = f"{custom_prefix_var.get()}_{session_start_time}_{extruder}"
    db.export_session_data(group_tag, session_folder)

db.create_database()

frame = ttk.Frame(root)
frame.grid(row=0, column=0, padx=10, pady=10)

video_labels = [ttk.Label(frame) for _ in caps]
for i, label in enumerate(video_labels):
    label.grid(row=0, column=i)

controls_frame = ttk.Frame(root)
controls_frame.grid(row=1, column=0, padx=10, pady=10)

print_speed_var = tk.StringVar(value="100")
layer_height_var = tk.StringVar(value="15")
extruder_var = tk.StringVar(value="SSE")

fields = [
    ("Print Speed:", print_speed_var),
    ("Layer Height:", layer_height_var),
    ("Capture Interval (s):", capture_interval_var)
]

for i, (label_text, var) in enumerate(fields):
    ttk.Label(controls_frame, text=label_text).grid(row=i, column=0, sticky="w")
    ttk.Entry(controls_frame, textvariable=var).grid(row=i, column=1)

extruder_label_row = len(fields)
ttk.Label(controls_frame, text="Extruder:").grid(row=extruder_label_row, column=0, sticky="w")
extruder_frame = ttk.Frame(controls_frame)
extruder_frame.grid(row=extruder_label_row, column=1, sticky="w")

ttk.Radiobutton(extruder_frame, text="Single-Screw Extruder", variable=extruder_var, value="SSE").pack(side=tk.LEFT)
ttk.Radiobutton(extruder_frame, text="Twin-Screw Extruder", variable=extruder_var, value="TWE").pack(side=tk.LEFT)

countdown_frame = ttk.Frame(controls_frame)
countdown_frame.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=5)
ttk.Label(countdown_frame, textvariable=countdown_var, foreground="blue", anchor="e").pack(side=tk.RIGHT)

session_config_frame = ttk.Frame(controls_frame)
session_config_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=5)

ttk.Label(session_config_frame, text="Folder Path:").grid(row=0, column=0, sticky="w")
ttk.Entry(session_config_frame, textvariable=folder_path_var, width=40).grid(row=0, column=1)
ttk.Button(session_config_frame, text="Browse", command=select_folder).grid(row=0, column=2, padx=5)

ttk.Label(session_config_frame, text="Folder Prefix:").grid(row=1, column=0, sticky="w")
ttk.Entry(session_config_frame, textvariable=custom_prefix_var).grid(row=1, column=1, columnspan=2, sticky="we")

button_frame = ttk.Frame(controls_frame)
button_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)

ttk.Button(button_frame, text="Create Session Folder", command=create_session_folder).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Capture", command=capture_and_save).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Start/Stop Capture", command=toggle_auto_capture).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Reconnect to Sensor", command=try_connect).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Export Session Data", command=export_session_data).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Quit", command=quit_program).pack(side=tk.RIGHT, padx=5)

status_frame = ttk.Frame(controls_frame)
status_frame.grid(row=len(fields)+3, column=0, columnspan=2)
ttk.Label(status_frame, text="Sensor Status:").pack(side=tk.LEFT)

status_label = tk.Label(status_frame, textvariable=connection_status_var, bg="red", fg="white", width=12)
status_label.pack(side=tk.LEFT, padx=5)

update_video()
root.mainloop()
