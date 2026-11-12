
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# OpenCV: Used for image processing and computer vision.
import cv2

# NumPy: Used for numerical operations on images and arrays.
import numpy as np

# Time: Provides time-related functions.
import time

# Sys: Allows us to modify Python's module search paths.
import sys

# Add the YOLOv8 source directory to Python's module search path.
# This allows Python to find the YOLOv8-related files and modules.
sys.path.append(
    '/home/jetson/yahboomcar_ws/src/yahboom_yolov8/yahboom_yolov8/yolov8'
)

# Import the YOLO class from the Ultralytics library.
from ultralytics import YOLO

# Load the pretrained YOLOv8 Nano model.
# yolov8n.pt is a lightweight model suitable for devices with limited resources.
model = YOLO(
    '/home/jetson/yahboomcar_ws/src/yahboom_yolov8/yahboom_yolov8/yolov8/weights/yolov8n.pt'
)

# Import ROS 2 Python client library.
import rclpy

# Import the base Node class used to create ROS 2 nodes.
from rclpy.node import Node

# Import the ROS 2 Image message type.
# This message type is used to send and receive camera images.
from sensor_msgs.msg import Image

# CvBridge converts between ROS Image messages and OpenCV images.
from cv_bridge import CvBridge


# ============================================================
# YOLOv8 OBJECT DETECTION AND TRACKING NODE
# ============================================================

class Yolov8_Track(Node):

    def __init__(self, name):

        # Initialize the ROS 2 node with the given name.
        super().__init__(name)

        # Create a CvBridge object for converting OpenCV images
        # into ROS 2 Image messages.
        self.rgb_bridge = CvBridge()

        # Create another CvBridge object for converting
        # ROS 2 Image messages into OpenCV images.
        self.msg2img_bridge = CvBridge()

        # Create a ROS 2 publisher.
        # It publishes the processed images containing detection results.
        #
        # Topic: detect_image
        # Message type: sensor_msgs/Image
        # Queue size: 1
        self.yolov8_img_pub = self.create_publisher(
            Image,
            "detect_image",
            1
        )

        # Subscribe to the RGB camera image topic.
        #
        # Topic: /camera/color/image_raw
        # Message type: sensor_msgs/Image
        # Callback: get_RGBImageCallBack
        # Queue size: 100
        #
        # Whenever a new camera image arrives, ROS 2 calls
        # get_RGBImageCallBack().
        self.sub_rgb = self.create_subscription(
            Image,
            "/camera/color/image_raw",
            self.get_RGBImageCallBack,
            100
        )

    # ========================================================
    # CAMERA IMAGE CALLBACK
    # ========================================================

    def get_RGBImageCallBack(self, rgb_msg):

        # Convert the incoming ROS 2 Image message into an OpenCV image.
        #
        # rgb8 means:
        #   R = Red channel
        #   G = Green channel
        #   B = Blue channel
        #
        # The result is a NumPy array containing the image pixels.
        rgb_image = self.msg2img_bridge.imgmsg_to_cv2(
            rgb_msg,
            "rgb8"
        )

        # Send the converted image to the YOLO processing function.
        self.process(rgb_image)

    # ========================================================
    # YOLOv8 OBJECT DETECTION AND TRACKING
    # ========================================================

    def process(self, frame):

        # Run YOLOv8 object tracking on the incoming camera image.
        #
        # model.track():
        #   Performs object detection and tracking.
        #
        # frame:
        #   The current camera image.
        #
        # persist=True:
        #   Keeps tracking information between consecutive frames.
        #   This helps YOLO maintain object identities across frames.
        results = model.track(
            frame,
            persist=True
        )

        # Print a separator to make terminal output easier to read.
        print("----------------------------------------------------------------------")

        # Print the detection and tracking results for the first image.
        #
        # results[0] contains the results for the current frame.
        # It can include:
        #   - Detected object classes
        #   - Confidence scores
        #   - Bounding box coordinates
        #   - Tracking IDs, when available
        print("res: ", results[0])

        print("----------------------------------------------------------------------")

        # Draw the detection results on the original image.
        #
        # plot() creates an annotated image containing information such as:
        #   - Bounding boxes around detected objects
        #   - Object class names
        #   - Confidence scores
        #   - Tracking IDs, when available
        annotated_frame = results[0].plot()

        # Convert the annotated OpenCV image into a ROS 2 Image message.
        #
        # encoding='rgb8' tells ROS 2 that the image uses
        # three color channels in RGB order.
        ros_image = self.rgb_bridge.cv2_to_imgmsg(
            annotated_frame,
            encoding='rgb8'
        )

        # Publish the processed image.
        # Other ROS 2 nodes can subscribe to the detect_image topic
        # to receive and display the YOLO detection results.
        self.yolov8_img_pub.publish(ros_image)


# ============================================================
# MAIN FUNCTION
# ============================================================

def main():

    # Initialize the ROS 2 communication system.
    rclpy.init()

    # Create an instance of the YOLOv8 tracking node.
    yolov8_track = Yolov8_Track('yolov8_track_node')

    # Keep the node running and process incoming ROS 2 messages.
    #
    # The node remains active until it receives a shutdown signal,
    # such as Ctrl+C in the terminal.
    rclpy.spin(yolov8_track)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

# This condition ensures that main() runs only when
# this Python file is executed directly.
if __name__ == '__main__':
    main()
