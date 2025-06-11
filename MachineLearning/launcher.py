import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import signal

class ScriptLauncher:
    def __init__(self, master):
        self.master = master
        master.title("Script Launcher")

        # Track subprocesses
        self.processes = {
            "optimizer": None,
            "wall": None,
            "logger": None
        }

        # UI Components for Optimizer
        self.optimizer_button = tk.Button(master, text="Start optimizer.py", command=self.start_optimizer)
        self.optimizer_button.grid(row=0, column=0, padx=10, pady=5)

        self.optimizer_stop_button = tk.Button(master, text="Stop", command=self.stop_optimizer)
        self.optimizer_stop_button.grid(row=0, column=1, padx=10)

        self.optimizer_status = tk.Label(master, text="Status: Stopped", fg="red")
        self.optimizer_status.grid(row=0, column=2, padx=10)

        # UI Components for Wall
        self.wall_button = tk.Button(master, text="Start wall.py", command=self.start_wall)
        self.wall_button.grid(row=1, column=0, padx=10, pady=5)

        self.wall_stop_button = tk.Button(master, text="Stop", command=self.stop_wall)
        self.wall_stop_button.grid(row=1, column=1, padx=10)

        self.wall_status = tk.Label(master, text="Status: Stopped", fg="red")
        self.wall_status.grid(row=1, column=2, padx=10)

        # UI Components for Data Logger
        self.logger_button = tk.Button(master, text="Start data_logger.py", command=self.start_logger)
        self.logger_button.grid(row=2, column=0, padx=10, pady=5)

        self.logger_stop_button = tk.Button(master, text="Stop", command=self.stop_logger)
        self.logger_stop_button.grid(row=2, column=1, padx=10)

        self.logger_status = tk.Label(master, text="Status: Stopped", fg="red")
        self.logger_status.grid(row=2, column=2, padx=10)

        # Exit button
        self.exit_button = tk.Button(master, text="Exit", command=self.exit_program)
        self.exit_button.grid(row=3, column=1, pady=10)

    # Launch and status update methods
    def start_script(self, name, script, label):
        if self.processes[name] is None or self.processes[name].poll() is not None:
            try:
                self.processes[name] = subprocess.Popen(["python", script])
                label.config(text="Status: Running", fg="green")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start {script}: {e}")
        else:
            messagebox.showinfo("Info", f"{script} is already running.")

    def stop_script(self, name, label):
        proc = self.processes.get(name)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                label.config(text="Status: Stopped", fg="red")
                self.processes[name] = None
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop {name}: {e}")
        else:
            label.config(text="Status: Stopped", fg="red")
            self.processes[name] = None

    # Script-specific start/stop methods
    def start_optimizer(self):
        self.start_script("optimizer", "optimizer.py", self.optimizer_status)

    def stop_optimizer(self):
        self.stop_script("optimizer", self.optimizer_status)

    def start_wall(self):
        self.start_script("wall", "wall.py", self.wall_status)

    def stop_wall(self):
        self.stop_script("wall", self.wall_status)

    def start_logger(self):
        self.start_script("logger", "data_logger.py", self.logger_status)

    def stop_logger(self):
        self.stop_script("logger", self.logger_status)

    def exit_program(self):
        # Attempt to stop all scripts on exit
        self.stop_optimizer()
        self.stop_wall()
        self.stop_logger()
        self.master.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScriptLauncher(root)
    root.mainloop()
