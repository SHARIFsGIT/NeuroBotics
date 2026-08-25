#!/usr/bin/env python3
"""Live lidar viewer: shows the /scan data as numbers in the terminal.

The lidar produces 360 distances per sweep - far too many to read raw.
This tool groups them into eight 45-degree sectors and prints the
NEAREST distance seen in each, twice a second, like a mini radar:

    front  0.85 m  <- obstacle ahead!
    right  3.20 m
    ...

The 360 rays sweep from -180 (behind) to +180 degrees, so bearing 0 is
dead ahead, negative is right, positive is left.

Prerequisites:
  1. source install/setup.bash
  2. ros2 launch neurobotics gazebo.launch.py
Then run:
  ros2 run neurobotics lidar_view.py

Also worth trying (no script needed):
  ros2 topic echo /scan --once     <- one full sweep, all 360 numbers
  ros2 topic hz /scan              <- how fast sweeps arrive (10 Hz)
  rviz2 -> add -> LaserScan        <- draw the rays in 3D

CTRL+C to quit.
"""

import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

# Sector layout: (name, centre bearing in degrees, half-width in degrees)
SECTORS = [
    ("front",    0, 22.5), ("f-right", -45, 22.5), ("right",  -90, 22.5),
    ("b-right", 135, 22.5), ("rear",   180, 22.5), ("b-left", -135, 22.5),
    ("left",     90, 22.5), ("f-left",   45, 22.5),
]
MIN_USEFUL = 0.2    # readings at/below this are the robot's own body


class LidarView(Node):
    def __init__(self):
        super().__init__('lidar_view')
        self.sub = self.create_subscription(
            LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.got = False
        self.create_timer(2.0, self.check_arrival)

    def check_arrival(self):
        if not self.got:
            self.get_logger().warn(
                "No data on '/scan' after 2 s. Is Gazebo running?")

    def on_scan(self, msg):
        self.got = True
        # 8 slots of nearest-distance-per-sector, plus the closest overall.
        best = [float('inf')] * 8
        overall, overall_bearing = float('inf'), 0.0
        # Beams that clip the robot's own chassis come back clamped at
        # range_min (0.200000003) - strictly ABOVE our 0.2 floor, so compare
        # against range_min plus a small epsilon, not against MIN_USEFUL alone.
        floor = max(MIN_USEFUL, msg.range_min + 0.01)
        for i, r in enumerate(msg.ranges):
            if not (floor < r < msg.range_max):
                continue      # nothing in range
            bearing = math.degrees(msg.angle_min + i * msg.angle_increment)
            # The lidar sits on the front-RIGHT corner, so the wedge of beams
            # that crosses over the chassis (+90..+150 deg, measured on this
            # robot: returns of 0.21-0.35 m there) is the robot's own body -
            # hide it, it would otherwise always look like a rear obstacle.
            if 90.0 <= bearing <= 150.0 and r < 0.5:
                continue
            if r < overall:
                overall, overall_bearing = r, bearing
            for s, (name, centre, half) in enumerate(SECTORS):
                # handle the wrap: -180 and +180 are both "rear"
                d = abs((bearing - centre + 180) % 360 - 180)
                if d <= half and r < best[s]:
                    best[s] = r
        line = "  ".join(
            f"{name:>7}:{' -- ' if b == float('inf') else f'{b:4.2f}'}m"
            for (name, _, _), b in zip(SECTORS, best))
        closest = ('nothing within range' if overall == float('inf')
                   else f"closest {overall:4.2f}m at "
                        f"{overall_bearing:+6.1f}deg (+ = left)")
        print(f"\r{line}   {closest}", end='', flush=True)


def main():
    try:
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    except Exception as e:
        print(f"[ERROR] Could not start ROS 2: {e}")
        print("Hint: run 'source /opt/ros/humble/setup.bash' and "
              "'source install/setup.bash' first.")
        sys.exit(1)

    node = LidarView()
    print("Lidar viewer - nearest obstacle per sector, twice a second. "
          "CTRL+C to quit.")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print("\nViewer stopped.")


if __name__ == '__main__':
    main()
