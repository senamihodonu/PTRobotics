import socket 
import time
import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import database_manager_mv as db
import layer_dimension as ld
import sys

# Set this flag to True to use URL cameras, False to disable them
USE_URL_CAMERAS = True

# Get the absolute path to the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate to the fanuc_ethernet_ip_drivers/src directory
pyp_path = os.path.normpath(
    os.path.join(current_dir, "..")
)

# Add the src path to sys.path
sys.path.append(pyp_path)

from PyPLCConnection import (
    PyPLCConnection,
    DISTANCE_SENSOR_IN, PLC_IP,
    DISTANCE_DATA_ADDRESS,
    ROBOT_IP
)

src_path = os.path.normpath(
    os.path.join(current_dir, "..", "..", "fanuc_ethernet_ip_drivers", "src")
)
sys.path.append(src_path)

from robot_controller import robot

woody = robot(ROBOT_IP)
plc = PyPLCConnection(PLC_IP)

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

root = tk.Tk()
root.title("Camera Monitoring and Data Capture")

# --- VARIABLES ---
custom_prefix_var = tk.StringVar(value="User")
folder_path_var = tk.StringVar(value=os.getcwd())
capture_interval_var = tk.StringVar(value="10")
countdown_var = tk.StringVar(value="")
connection_status_var = tk.StringVar(value="Disconnected")

CAMERA_URLS = [
    # "http://172.29.172.128:8080/video",
    "http://172.29.179.38:8080/video"
]

caps = []
if USE_URL_CAMERAS:
    caps = [cv2.VideoCapture(url) for url in CAMERA_URLS]
    caps = [cap if cap.isOpened() else None for cap in caps]

vision_camera = cv2.VideoCapture(0)
vision_camera = vision_camera if vision_camera.isOpened() else None

SERVER_IP = '172.29.143.185'
SERVER_PORT = 5001
client = None
socket_connected = False

temperature = None
humidity = None
photo_count = 0
collecting_data = False
paused = False
session_folder = None
session_start_time = None
countdown_seconds = 0

width = None

# --- FUNCTIONS ---
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
        client.connect((SERVER_IP, SERVER_PORT))
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
    global temperature, humidity, socket_connected, client, width
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

def get_nozzle_height():
    return plc.read_single_register(DISTANCE_DATA_ADDRESS)

def get_print_speed():
    return woody.get_actual_robot_speed()

def capture_and_save():
    global temperature, humidity, photo_count, socket_connected, session_folder, session_start_time
    if not session_folder:
        create_session_folder()

    fetch_sensor_data()
    rets, frames = zip(*[(cap.read() if cap else (False, None)) for cap in caps]) if USE_URL_CAMERAS else ([], [])

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    photo_count += 1
    print_tag = f"{timestamp}_p{photo_count}"

    try:
        extruder = extruder_var.get()
    except ValueError:
        log("Invalid input! Using default print_speed=50.")
        extruder = "SSE"

    group_tag = f"{custom_prefix_var.get()}_{session_start_time}_{extruder}"
    print_speed = get_print_speed()

    overlay_lines = [
        f"Tag: {print_tag}",
        f"Temp: {temperature:.1f}°C" if temperature is not None else "Temp: N/A",
        f"Humidity: {humidity:.1f}%" if humidity is not None else "Humidity: N/A",
        f"Extruder: {extruder}",
        f"Print Speed: {print_speed} mm/min",
        f"Group: {group_tag}"
    ]

    image_tags = []

    if USE_URL_CAMERAS:
        for idx, (ret, frame) in enumerate(zip(rets, frames)):
            if ret and frame is not None:
                image_name = f"c{idx+1}_{timestamp}.jpg"
                image_path = os.path.join(session_folder, image_name)

                for i, line in enumerate(overlay_lines):
                    y_pos = frame.shape[0] - 10 - i * 25
                    cv2.putText(frame, line, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

                cv2.imwrite(image_path, frame)
                image_tags.append(image_name)
            else:
                image_tags.append(None)

    # Process vision camera
    width_mm = None
    mv_image_name = None
    if vision_camera:
        ret, vision_frame = vision_camera.read()
        if ret:
            timestamp_mv = f"{timestamp}"
            mv_image_name = f"c_{timestamp_mv}.jpg"
            mv_image_path = os.path.join(session_folder, mv_image_name)
            cv2.imwrite(mv_image_path, vision_frame)

            width_mm, height_mm = ld.process_image(vision_frame.copy(), mv_image_name, timestamp_mv)
            if width_mm is not None:
                log(f"Vision Camera Measurement — Width: {width_mm:.2f} mm, Height: {height_mm:.2f} mm")
        else:
            log("Failed to read from vision camera for measurement.")

    vision_capture = mv_image_name if vision_camera and ret else None
    nozzle_height = get_nozzle_height()
    print_speed = get_print_speed()

    db.insert_print_data(
        group_tag, print_tag,
        image_tags[0] if len(image_tags) > 0 else None,
        image_tags[1] if len(image_tags) > 1 else None,
        vision_capture,
        humidity, temperature, print_speed,
        width_mm, height_mm,
        nozzle_height
    )

    log(f"Data saved: {print_tag}, Temp: {temperature}, Humidity: {humidity}, Width: {width_mm}, Height: {height_mm}, Group: {group_tag}")

def update_video():
    frames = []
    if USE_URL_CAMERAS:
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

    if vision_camera:
        ret, frame = vision_camera.read()
        if ret:
            frame = cv2.resize(frame, (240, 180))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            vision_image = ImageTk.PhotoImage(Image.fromarray(frame))
            frames.append(vision_image)
        else:
            frames.append(None)

    for label, frame in zip(video_labels, frames):
        if frame:
            label.config(image=frame)
            label.image = frame
        else:
            label.config(image="")

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
    if paused:
        root.after(1000, auto_capture)
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
    if not collecting_data or paused:
        countdown_var.set("")
        return
    countdown_var.set(f"Next capture in: {countdown_seconds}s")
    countdown_seconds -= 1
    root.after(1000, update_countdown)

def toggle_pause():
    global paused
    paused = not paused
    if paused:
        paused_label.grid()
        blink_paused_label()
        root.config(bg="yellow")
    else:
        paused_label.grid_remove()
        root.config(bg="SystemButtonFace")
        countdown_var.set("")
        update_countdown()

def blink_paused_label():
    if not paused:
        return
    current_text = paused_label.cget("text")
    paused_label.config(text="PAUSED" if current_text == "" else "")
    root.after(500, blink_paused_label)

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

# --- GUI SETUP ---
db.create_database()

frame = ttk.Frame(root)
frame.grid(row=0, column=0, padx=10, pady=10)

video_labels = []
if USE_URL_CAMERAS:
    video_labels = [ttk.Label(frame) for _ in caps]

if vision_camera:
    vision_label = ttk.Label(frame)
    video_labels.append(vision_label)
    vision_label.grid(row=0, column=len(video_labels) - 1)

for i, label in enumerate(video_labels):
    label.grid(row=0, column=i)

controls_frame = ttk.Frame(root)
controls_frame.grid(row=1, column=0, padx=10, pady=10)

extruder_var = tk.StringVar(value="SSE")
comment_var = tk.StringVar()

fields = [
    ("Comment:", comment_var),
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

ttk.Label(session_config_frame, text="User name or initial:").grid(row=1, column=0, sticky="w")
ttk.Entry(session_config_frame, textvariable=custom_prefix_var).grid(row=1, column=1, columnspan=2, sticky="we")

button_frame = ttk.Frame(controls_frame)
button_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)

ttk.Button(button_frame, text="Capture", command=capture_and_save).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Start/Stop Capture", command=toggle_auto_capture).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Pause/Resume", command=toggle_pause).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Reconnect to Sensor", command=try_connect).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Export Session Data", command=export_session_data).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="Quit", command=quit_program).pack(side=tk.RIGHT, padx=5)

status_frame = ttk.Frame(controls_frame)
status_frame.grid(row=len(fields)+3, column=0, columnspan=2)
ttk.Label(status_frame, text="Sensor Status:").pack(side=tk.LEFT)

status_label = tk.Label(status_frame, textvariable=connection_status_var, bg="red", fg="white", width=12)
status_label.pack(side=tk.LEFT, padx=5)

paused_label = tk.Label(root, text="PAUSED", font=("Arial", 48), fg="red", bg="yellow")
paused_label.grid(row=2, column=0, pady=10)
paused_label.grid_remove()

update_video()
root.mainloop()
