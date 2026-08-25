#!/usr/bin/env python3
"""Obstacle avoidance for the Neurobotics Gazebo simulation.

Reads the 360-degree /scan topic. When something is closer than SAFE_DIST
in the front 90-degree sector (bearings -45 deg .. +45 deg), the robot
slows down and steers away from the obstacle's side of the sector; if it
gets closer than STOP_DIST it stops and turns in place. Once the path is
clear again it steers back to the heading it had before the obstacle, so
it resumes its original course instead of wandering off diagonally.

Heading comes from the IMU (/imu), not wheel odometry: odometry cannot see
rotation that happens through tyre scrub, so a heading lock based on it
slowly arcs away.

Prerequisites:
  1. source install/setup.bash
  2. ros2 launch neurobotics gazebo.launch.py
Then run:
  ros2 run neurobotics obstacle_avoid.py

NOTE: keep the arm upright while this runs - if the arm is folded
forward the lidar sees it as an obstacle right in front of the robot.

Stop with CTRL+C (the robot halts on exit).
"""

import sys

import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu, LaserScan
import math

SAFE_DIST = 0.85    # start reacting at 85 cm. Needs to be this far because
                    # the lidar sits on the front-RIGHT corner: a box 0.6 m
                    # left of the line stays >= 0.77 m away while inside the
                    # 45-deg front sector - with 0.5 the robot would never
                    # even see the left-side boxes
STOP_DIST = 0.35    # too close: stop and turn in place
HALF_FOV = 0.7854   # front sector half-angle: 45 deg each side of dead ahead
MIN_USEFUL = 0.2    # readings at/below this are the robot's own body (the
                    # lidar sits on the chassis corner; near-body beams clip
                    # it) or below the sensor's min range - never obstacles
TURN = 0.6          # rad/s steering rate when avoiding
KP_HEAD = 1.5       # how hard to steer back to the course heading


class ObstacleAvoid(Node):
    def __init__(self):
        super().__init__('obstacle_avoid')
        self.pub = self.create_publisher(Twist, '/diff_cont/cmd_vel_unstamped', 10)
        self.sub = self.create_subscription(
            LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.odom = self.create_subscription(
            Odometry, '/diff_cont/odom', self.on_odom, 10)
        self.imu = self.create_subscription(Imu, '/imu', self.on_imu, 10)
        self.front_min = 99.0
        self.front_bearing = 0.0
        self.last_turn = -TURN      # remembered direction for dead-ahead obstacles
        self.yaw = 0.0              # current heading (IMU preferred, odom fallback)
        self.have_imu = False
        self.target_heading = None  # the course heading (latched once, then held)
        self.got_first_scan = False
        self.create_timer(5.0, self.check_scan_arrival)
        self.create_timer(0.1, self.control_loop)

    def check_scan_arrival(self):
        if not self.got_first_scan:
            self.get_logger().warn(
                "No data on '/scan' after 5 s. Check that Gazebo is running: "
                "'ros2 topic hz /scan'")

    def on_odom(self, msg):
        # Fallback heading from wheel odometry (used until the IMU speaks)
        if self.have_imu:
            return
        q = msg.pose.pose.orientation
        self.yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                              1.0 - 2.0 * (q.y * q.y + q.z * q.z))

    def on_imu(self, msg):
        # Heading from the IMU - trustworthy even when the body rotates
        # through tyre scrub, which wheel odometry cannot see.
        self.have_imu = True
        q = msg.orientation
        self.yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                              1.0 - 2.0 * (q.y * q.y + q.z * q.z))

    def on_scan(self, msg):
        self.got_first_scan = True
        # Front sector by BEARING, not by array position: the scan is a full
        # 360 deg sweep starting at angle_min = -pi, so beam i has bearing
        # angle_min + i * angle_increment and dead ahead (bearing 0) sits in
        # the MIDDLE of the array - slicing the first/last eighth of the
        # array would look at the robot's rear instead.
        best, best_bearing = 99.0, 0.0
        for i, r in enumerate(msg.ranges):
            if MIN_USEFUL < r < msg.range_max:
                bearing = msg.angle_min + i * msg.angle_increment
                if abs(bearing) <= HALF_FOV and r < best:
                    best = r
                    best_bearing = bearing
        self.front_min, self.front_bearing = best, best_bearing

    def control_loop(self):
        cmd = Twist()
        if not self.got_first_scan:
            self.pub.publish(cmd)              # stand still until the lidar speaks
            return
        if self.target_heading is None and self.got_first_scan:
            # Latch the course heading once, then always steer back to it -
            # this also cancels the robot's slight natural pull to one side.
            self.target_heading = self.yaw
        d = self.front_min
        if d > SAFE_DIST:                      # clear path: drive and hold heading
            err = self.target_heading - self.yaw
            err = math.atan2(math.sin(err), math.cos(err))   # wrap to +-pi
            cmd.linear.x = 0.2
            cmd.angular.z = max(-TURN, min(TURN, KP_HEAD * err))
        else:
            # Steer AWAY from the side of the sector the obstacle sits in:
            # obstacle on the right half (bearing < 0) -> turn left, and
            # vice versa. Dead ahead -> keep turning the way we were.
            if self.front_bearing < -0.02:
                turn = TURN
            elif self.front_bearing > 0.02:
                turn = -TURN
            else:
                turn = self.last_turn
            self.last_turn = turn
            if d < STOP_DIST:                  # too close: pivot, no forward speed
                cmd.angular.z = turn
            else:                              # getting close: creep around it
                cmd.linear.x = 0.05
                cmd.angular.z = turn
        self.pub.publish(cmd)


def main():
    try:
        # NO = let CTRL+C raise a normal KeyboardInterrupt so the cleanup
        # below can still publish the halt command (rclpy's default handler
        # shuts the context down first and the publish would fail).
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    except Exception as e:
        print(f"[ERROR] Could not start ROS 2: {e}")
        print("Hint: run 'source /opt/ros/humble/setup.bash' and "
              "'source install/setup.bash' first.")
        sys.exit(1)

    node = ObstacleAvoid()
    print("Obstacle avoidance running (drives forward, steers around "
          "obstacles). CTRL+C to stop.")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.pub.publish(Twist())   # stop robot on exit
        except Exception as e:
            print(f"[WARN] could not send halt: {e}")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print("Obstacle avoidance stopped. Robot halted.")


if __name__ == '__main__':
    main()
