#!/usr/bin/env python3
"""Line follower for the Neurobotics Gazebo simulation.

Detects the black line on the white floor with OpenCV and steers to keep
it centred. Two debug windows (raw ROI + binary mask) open on screen.

The camera looks straight out along the arm's tool axis (it is the DCW2
camera mounted on the arm). With the arm straight (HOME) the camera points
at the sky and sees no line at all — so this script first bends the arm
forward into ARM_POSE, which aims the camera down at the floor about
0.4–1.4 m ahead of the robot. The arm is returned to HOME on exit.

Prerequisites:
  1. source install/setup.bash
  2. ros2 launch neurobotics gazebo.launch.py
Then run:
  ros2 run neurobotics line_follow.py            (default topic /camera/image_raw)
  ros2 run neurobotics line_follow.py <topic>    (custom image topic)

Stop with CTRL+C (the robot halts and the arm returns to HOME).
"""

import os
import sys
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from std_msgs.msg import Float64MultiArray

# Arm pose that aims the camera at the floor: joints [arm1..arm4] in radians
# (arm1 = turn base, arm2..arm4 = bend forward). With the camera looking
# along the arm, bending these three joints forward tilts the camera about
# 40 degrees down, so the line shows up centred in the lower half of the
# image. The remaining 7 values (arm5 + gripper fingers) stay at 0.
ARM_POSE = [0.0, -0.70, -0.70, -0.87] + [0.0] * 7
HOME_POSE = [0.0] * 11


def to_cv(msg):
    """Convert a sensor_msgs/Image to an OpenCV array (BGR or gray)."""
    h, w = msg.height, msg.width
    arr = np.frombuffer(msg.data, dtype=np.uint8)
    enc = msg.encoding.lower()
    if enc == 'rgb8':
        return arr.reshape(h, w, 3)[:, :, ::-1].copy()     # RGB -> BGR
    if enc == 'bgr8':
        return arr.reshape(h, w, 3).copy()
    if enc in ('mono8', '8uc1'):
        return arr.reshape(h, w).copy()
    raise ValueError('unsupported encoding: ' + enc)


def ramp_to(pub, target, steps=40, dt=0.1):
    """Move the arm to `target` smoothly instead of in one jump.

    A single big command makes the arm snap into position, and the kick
    physically shoves the whole robot (the base rocks on its wheels).
    Small steps with an ease-in/ease-out profile move it gently.
    """
    start = time.time()
    for i in range(1, steps + 1):
        frac = i / steps
        ease = frac * frac * (3 - 2 * frac)          # smooth start and stop
        msg = Float64MultiArray()
        msg.data = [v * ease for v in target]
        pub.publish(msg)
        time.sleep(dt)
    return time.time() - start


class LineFollower(Node):
    def __init__(self, topic):
        super().__init__('line_follower')
        self.pub = self.create_publisher(Twist, '/diff_cont/cmd_vel_unstamped', 10)
        self.arm_pub = self.create_publisher(Float64MultiArray,
                                             '/arm_cont/commands', 10)
        self.sub = self.create_subscription(Image, topic, self.on_image,
                                            qos_profile_sensor_data)
        # ---- Tuning parameters ----
        self.speed = 0.15        # m/s forward speed
        self.kp = 2.5            # steering aggressiveness
        self.max_turn = 1.0      # rad/s clamp
        self.min_pixels = 50     # below this the line counts as "lost"
        self.lost = 0
        self.got_first_image = False
        # Debug windows only when a display is available (over plain SSH the
        # script still follows the line, just without the preview).
        self.show_windows = bool(os.environ.get('DISPLAY'))
        # Watchdog: tell the user if no camera images ever arrive.
        self.create_timer(5.0, self.check_image_arrival)

    def check_image_arrival(self):
        if not self.got_first_image:
            self.get_logger().warn(
                f"No images on '{self.sub.topic_name}' after 5 s. Check that "
                "Gazebo is running and the camera sensor exists: "
                "'ros2 topic hz /camera/image_raw'")

    def on_image(self, msg):
        self.got_first_image = True
        frame = to_cv(msg)
        h, w = frame.shape[:2]

        roi = frame[int(h * 0.55):, :]                      # bottom part of view
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)

        pixels = cv2.findNonZero(mask)
        cmd = Twist()

        if pixels is not None and len(pixels) > self.min_pixels:
            cx = float(np.mean(pixels[:, :, 0]))
            error = cx - w / 2.0
            cmd.linear.x = self.speed
            cmd.angular.z = -float(np.clip(self.kp * error / (w / 2.0),
                                           -self.max_turn, self.max_turn))
            self.lost = 0
            cv2.circle(roi, (int(cx), roi.shape[0] // 2), 8, (0, 0, 255), -1)
            cv2.putText(roi, f'err {error:.0f}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            self.lost += 1
            if self.lost > 5:
                cmd.angular.z = 0.4                          # search for the line

        self.pub.publish(cmd)
        if self.show_windows:
            cv2.imshow('view', roi)
            cv2.imshow('mask', mask)
            cv2.waitKey(1)


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else '/camera/image_raw'
    try:
        # SignalHandlerOptions.NO: let CTRL+C raise a normal Python
        # KeyboardInterrupt instead of rclpy tearing ROS down immediately —
        # otherwise the cleanup below (stop robot, arm back to HOME) could
        # not publish anything.
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    except Exception as e:
        print(f"[ERROR] Could not start ROS 2: {e}")
        print("Hint: run 'source /opt/ros/humble/setup.bash' and "
              "'source install/setup.bash' first.")
        sys.exit(1)

    node = LineFollower(topic)

    # 1. Lock the base before touching the arm. Publishing a zero Twist once
    #    makes the wheel controllers actively hold still — without it the
    #    robot slowly creeps and rotates on its own in this simulation, and
    #    any arm motion would shove it around.
    node.pub.publish(Twist())

    # 2. Wait for the arm controller (it starts with the simulation; if the
    #    sim is still coming up our commands would be silently dropped).
    t0 = time.time()
    while node.arm_pub.get_subscription_count() == 0 and time.time() - t0 < 10:
        node.pub.publish(Twist())      # keep the base locked while waiting
        time.sleep(0.2)
    if node.arm_pub.get_subscription_count() == 0:
        print("[WARN] No arm controller found — the arm will NOT be posed, "
              "the camera stays looking at the sky. Is the simulation up?")

    # 3. Bend the arm forward so the camera can see the floor.
    print("Posing the arm so the camera looks at the floor ...")
    ramp_to(node.arm_pub, ARM_POSE)

    print(f"Line follower running on topic '{topic}'. CTRL+C to stop.")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.pub.publish(Twist())      # halt robot
            ramp_to(node.arm_pub, HOME_POSE, steps=20, dt=0.05)  # arm back up
        except Exception as e:
            print(f"[WARN] cleanup incomplete: {e}")
        if node.show_windows:
            cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print("Line follower stopped. Robot halted, arm back at HOME.")


if __name__ == '__main__':
    main()
