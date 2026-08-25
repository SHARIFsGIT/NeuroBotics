#!/usr/bin/env python3
"""Slider GUI for the 5-DOF arm and gripper in the Gazebo simulation.

Publishes position commands to /arm_cont/commands (11 values). Gazebo
Classic does not simulate <mimic> joints, so the finger joints are
commanded explicitly with the same coupling signs as the URDF.

Prerequisites:
  1. source install/setup.bash
  2. ros2 launch neurobotics gazebo.launch.py
Then run:
  ros2 run neurobotics arm_gui.py
"""

import sys
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import Float64MultiArray

# (label, min rad, max rad) - limits taken from the URDF
JOINTS = [
    ("J1  Base",     -1.5708, 1.5708),
    ("J2  Shoulder", -1.5708, 1.5708),
    ("J3  Elbow",    -1.5708, 1.5708),
    ("J4  Wrist",    -1.5708, 1.5708),
    ("J5  Rotate",   -1.5708, 3.1416),
    ("Gripper",      -1.5400, 0.0000),
]

BG     = "#20232a"
PANEL  = "#2a2e37"
FG     = "#e9ecf1"
MUTED  = "#9aa3b2"
ACCENT = "#4f8cff"
GREEN  = "#2f9e63"
RED    = "#c94f4f"
DEG    = 57.29578


class ArmGUI(Node):
    def __init__(self, root):
        super().__init__("neurobotics_arm_gui")
        self.pub = self.create_publisher(Float64MultiArray, "/arm_cont/commands", 10)

        self.root = root
        root.title("Neurobotics - Arm Control Panel")
        root.configure(bg=BG)
        root.resizable(False, False)

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TScale", background=PANEL, troughcolor="#15171c")

        header = tk.Frame(root, bg=ACCENT)
        header.pack(fill="x")
        tk.Label(header, text="ARM CONTROL", fg="white", bg=ACCENT,
                 font=("Segoe UI", 14, "bold"), padx=14, pady=8).pack(side="left")
        tk.Label(header, text="Gazebo simulation", fg="#dbe6ff", bg=ACCENT,
                 font=("Segoe UI", 9), padx=10).pack(side="right")

        body = tk.Frame(root, bg=BG, padx=14, pady=10)
        body.pack(fill="both", expand=True)

        self.vars, self.value_labels = [], []
        for i, (name, lo, hi) in enumerate(JOINTS):
            tk.Label(body, text=name, fg=FG, bg=BG,
                     font=("Segoe UI", 10, "bold"), width=12,
                     anchor="w").grid(row=i, column=0, sticky="w", pady=5)
            v = tk.DoubleVar(value=0.0)
            self.vars.append(v)
            ttk.Scale(body, from_=lo, to=hi, variable=v, length=260,
                      command=lambda *_: self.refresh()
                      ).grid(row=i, column=1, padx=12)
            lbl = tk.Label(body, text="   0.0 deg", fg=MUTED, bg=BG,
                           font=("Consolas", 10), width=10, anchor="e")
            lbl.grid(row=i, column=2)
            self.value_labels.append(lbl)

        btns = tk.Frame(root, bg=BG, pady=10)
        btns.pack()
        for text, cmd, color in [
            ("HOME", self.home, ACCENT),
            ("OPEN GRIPPER", lambda: self.set_gripper(0.0), GREEN),
            ("CLOSE GRIPPER", lambda: self.set_gripper(-1.54), RED),
        ]:
            tk.Button(btns, text=text, command=cmd, bg=color, fg="white",
                      activebackground="#ffffff22", relief="flat",
                      font=("Segoe UI", 10, "bold"), padx=14, pady=6,
                      cursor="hand2").pack(side="left", padx=6)

        self.status = tk.Label(root, text="Publishing at 10 Hz - home = 0 rad (straight)",
                               fg=MUTED, bg=BG, font=("Segoe UI", 9), pady=6)
        self.status.pack()

        self.tick()

    def refresh(self):
        for v, lbl in zip(self.vars, self.value_labels):
            lbl.config(text=f"{v.get()*DEG:6.1f} deg")

    def home(self):
        for v in self.vars:
            v.set(0.0)
        self.refresh()

    def set_gripper(self, value):
        self.vars[5].set(value)
        self.refresh()

    def build_msg(self):
        a = [v.get() for v in self.vars]          # arm1..arm5 + gripper (rlink1)
        g = a[5]
        # Finger joints mimic the gripper joint with these signs:
        # rlink2:+g  llink1:+g  llink2:-g  rlink3:-g  llink3:+g
        m = Float64MultiArray()
        m.data = a + [g, g, -g, -g, g]
        return m

    def tick(self):
        try:
            rclpy.spin_once(self, timeout_sec=0)
            self.pub.publish(self.build_msg())
        except Exception:
            return          # ROS was shut down (e.g. CTRL+C) - stop ticking
        self.root.after(100, self.tick)


def main():
    try:
        # NO = let CTRL+C raise a normal KeyboardInterrupt so the cleanup
        # below runs; rclpy's default handler would tear ROS down first and
        # every 100 ms publish would throw a traceback instead.
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    except Exception as e:
        print(f"[ERROR] Could not start ROS 2: {e}")
        print("Hint: run 'source /opt/ros/humble/setup.bash' and "
              "'source install/setup.bash' first.")
        sys.exit(1)

    root = tk.Tk()
    gui = ArmGUI(root)
    try:
        root.mainloop()
    finally:
        gui.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
