
# ============================================================
# 1. IMPORT REQUIRED LIBRARIES
# ============================================================

# OpenCV is used for image processing and displaying camera images.
import cv2

# Operating system functions for working with files and directories.
import os

# Import the ROS 2 Image message type.
from sensor_msgs.msg import Image

# Message filters allow us to synchronize messages from ROS 2 topics.
import message_filters

# CvBridge converts ROS 2 Image messages into OpenCV images.
from cv_bridge import CvBridge

# Import OpenCV again with the shorter name cv.
import cv2 as cv

# Import the custom message used to control the six robot arm joints.
from arm_msgs.msg import ArmJoints

# Provides time-related functions, such as time.time() and sleep().
import time

# Import all functions and classes from the project's media_library module.
# This module provides the HandDetector class used for hand detection
# and gesture recognition.
from M3Pro_demo.media_library import *

# Import the ROS 2 Node class.
from rclpy.node import Node

# Import the ROS 2 Python client library.
import rclpy

# Import message-filter subscriber and synchronization tools.
from message_filters import (
    Subscriber,
    TimeSynchronizer,
    ApproximateTimeSynchronizer
)

# Python threading allows us to execute a function in a separate thread.
import threading


# Print a message indicating that the imports have been completed.
print('init done')


# ============================================================
# 2. CREATE THE MEDIAPIPE DETECTION ROS 2 NODE
# ============================================================

class MediapipeDetectNode(Node):

    def __init__(self, name):

        # Initialize the parent ROS 2 Node class.
        super().__init__(name)

        # ----------------------------------------------------
        # INITIAL ROBOT ARM JOINT POSITIONS
        # ----------------------------------------------------

        # Initial positions for the six robot arm joints.
        #
        # joint1 = 90 degrees
        # joint2 = 150 degrees
        # joint3 = 12 degrees
        # joint4 = 20 degrees
        # joint5 = 90 degrees
        # joint6 = 0 degrees
        self.init_joints = [90, 150, 12, 20, 90, 0]

        # ----------------------------------------------------
        # IMAGE CONVERSION
        # ----------------------------------------------------

        # Create a CvBridge object for RGB camera images.
        self.rgb_bridge = CvBridge()

        # Create another CvBridge object for depth camera images.
        # It is initialized here, although this code does not
        # currently process depth images.
        self.depth_bridge = CvBridge()

        # ----------------------------------------------------
        # HAND DETECTOR INITIALIZATION
        # ----------------------------------------------------

        # Create an instance of the HandDetector class.
        #
        # HandDetector comes from the project's media_library module.
        # It is responsible for detecting hands and recognizing gestures.
        self.hand_detector = HandDetector()

        # Store the current time.
        # This variable is initialized but not used elsewhere
        # in the shown code.
        self.pr_time = time.time()

        # Store the previous processing time.
        # This value is used to calculate frames per second (FPS).
        self.pTime = time.time()

        # ----------------------------------------------------
        # ROBOT ARM PUBLISHER
        # ----------------------------------------------------

        # Create a publisher for sending six joint target angles.
        #
        # Topic: arm6_joints
        # Message type: ArmJoints
        # Queue size: 10
        self.TargetAngle_pub = self.create_publisher(
            ArmJoints,
            "arm6_joints",
            10
        )

        # ----------------------------------------------------
        # RGB CAMERA SUBSCRIBER
        # ----------------------------------------------------

        # Subscribe to the RGB camera image topic.
        #
        # Topic: /camera/color/image_raw
        #
        # Subscriber from message_filters is used so that
        # the image can be handled through a synchronization callback.
        self.rgb_image_sub = Subscriber(
            self,
            Image,
            '/camera/color/image_raw'
        )

        # ----------------------------------------------------
        # WAIT FOR ROBOT ARM CONNECTION
        # ----------------------------------------------------

        # Check whether another ROS 2 node has subscribed
        # to the arm6_joints topic.
        #
        # If there is no subscriber, repeatedly publish
        # the initial joint positions.
        while not self.TargetAngle_pub.get_subscription_count():

            # Publish the initial arm position.
            self.pubSix_Arm(self.init_joints)

            # Wait for 0.1 seconds before checking again.
            time.sleep(0.1)

        # Once a subscriber is available, publish the initial
        # joint positions one more time.
        self.pubSix_Arm(self.init_joints)

        # ----------------------------------------------------
        # REGISTER CAMERA IMAGE CALLBACK
        # ----------------------------------------------------

        # Create an ApproximateTimeSynchronizer.
        #
        # In this case, only one topic is provided:
        # the RGB camera image topic.
        #
        # Parameters:
        #   [self.rgb_image_sub] = subscriber list.
        #   1 = message queue size.
        #   0.5 = allowed timestamp difference in seconds.
        self.ts = ApproximateTimeSynchronizer(
            [self.rgb_image_sub],
            1,
            0.5
        )

        # Register the callback function.
        # Whenever an RGB image is received, callback() is executed.
        self.ts.registerCallback(self.callback)

        # Wait for two seconds.
        time.sleep(2)

        # Initialize the gesture-related start time.
        # This variable is initialized but not used elsewhere
        # in the shown code.
        self.start_time = 0.0


    # ========================================================
    # 3. PUBLISH SIX ROBOT ARM JOINT ANGLES
    # ========================================================

    def pubSix_Arm(self, joints, id=6, angle=180.0, runtime=2000):

        # Create a new ArmJoints message.
        arm_joint = ArmJoints()

        # Assign the first joint angle.
        arm_joint.joint1 = joints[0]

        # Assign the second joint angle.
        arm_joint.joint2 = joints[1]

        # Assign the third joint angle.
        arm_joint.joint3 = joints[2]

        # Assign the fourth joint angle.
        arm_joint.joint4 = joints[3]

        # Assign the fifth joint angle.
        arm_joint.joint5 = joints[4]

        # Assign the sixth joint angle.
        arm_joint.joint6 = joints[5]

        # Set the duration of the arm movement.
        # The default value is 2000 milliseconds.
        arm_joint.time = runtime

        # Publish the joint angles to the arm6_joints topic.
        self.TargetAngle_pub.publish(arm_joint)


    # ========================================================
    # 4. RGB CAMERA IMAGE CALLBACK
    # ========================================================

    # This function is called whenever a new RGB image
    # arrives from the camera.
    def callback(self, color_msg):

        # Convert the ROS 2 Image message into an OpenCV image.
        #
        # "bgr8" means:
        #   B = Blue channel
        #   G = Green channel
        #   R = Red channel
        #
        # OpenCV commonly uses BGR image format.
        rgb_image = self.rgb_bridge.imgmsg_to_cv2(
            color_msg,
            "bgr8"
        )

        # Send the converted image to the hand-processing function.
        self.process(rgb_image)


    # ========================================================
    # 5. PROCESS CAMERA IMAGE AND DETECT HANDS
    # ========================================================

    def process(self, frame):

        # ----------------------------------------------------
        # HAND DETECTION
        # ----------------------------------------------------

        # Detect hands in the current camera frame.
        #
        # findHands() returns three values:
        #
        # frame:
        #   The image with hand detection drawings.
        #
        # lmList:
        #   The hand landmark coordinates.
        #
        # bbox:
        #   The bounding box around the detected hand.
        #
        # The exact structure of these values depends on
        # the HandDetector implementation in media_library.
        frame, lmList, bbox = self.hand_detector.findHands(frame)

        # ----------------------------------------------------
        # CHECK WHETHER A HAND WAS DETECTED
        # ----------------------------------------------------

        # Check whether the landmark list contains any points.
        #
        # If its length is not zero, at least one hand has been detected.
        if len(lmList) != 0:

            # Create a new thread to recognize the hand gesture.
            #
            # threading.Thread() allows the gesture-recognition
            # function to execute in a separate thread.
            #
            # target:
            #   The function that should run in the thread.
            #
            # args:
            #   The arguments passed to that function.
            gesture = threading.Thread(
                target=self.Gesture_Detect_threading,
                args=(lmList, bbox)
            )

            # Start the gesture-recognition thread.
            gesture.start()

            # Wait until the thread finishes execution.
            #
            # join() makes the main processing function wait
            # for the gesture-recognition thread to complete.
            gesture.join()

        # ----------------------------------------------------
        # CALCULATE FRAMES PER SECOND (FPS)
        # ----------------------------------------------------

        # Get the current time.
        cTime = time.time()

        # Calculate FPS.
        #
        # FPS = 1 / time taken for one frame.
        #
        # cTime - self.pTime represents the time between
        # the current frame and the previous frame.
        fps = 1 / (cTime - self.pTime)

        # Update the previous processing time.
        self.pTime = cTime

        # Convert the FPS value into text.
        # int(fps) removes the decimal portion.
        text = "FPS : " + str(int(fps))

        # Display the FPS value on the camera image.
        #
        # Parameters:
        #   frame = image where the text is drawn.
        #   text = FPS information.
        #   (20, 30) = text position.
        #   FONT_HERSHEY_SIMPLEX = font style.
        #   0.9 = font size.
        #   (0, 0, 255) = red colour in BGR format.
        #   1 = text thickness.
        cv.putText(
            frame,
            text,
            (20, 30),
            cv.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            1
        )

        # This commented line could be used to publish the processed
        # image through another ROS 2 image publisher if self.media_ros
        # were configured elsewhere.
        # self.media_ros.pub_imgMsg(frame)

        # ----------------------------------------------------
        # CHECK KEYBOARD INPUT
        # ----------------------------------------------------

        # Check whether the user has pressed the Q key.
        #
        # cv.waitKey(1) waits approximately 1 millisecond
        # and processes OpenCV window events.
        #
        # & 0xFF extracts the lower 8 bits of the key value.
        if cv.waitKey(1) & 0xFF == ord('q'):

            # Close all OpenCV display windows.
            cv.destroyAllWindows()

        # ----------------------------------------------------
        # DISPLAY THE CAMERA IMAGE
        # ----------------------------------------------------

        # Display the processed camera frame.
        # The window is named "frame".
        cv.imshow('frame', frame)


    # ========================================================
    # 6. RECOGNIZE HAND GESTURE USING A SEPARATE THREAD
    # ========================================================

    def Gesture_Detect_threading(self, lmList, bbox):

        # Send the detected hand landmarks to the gesture-recognition
        # function provided by HandDetector.
        #
        # get_gesture() analyzes the hand landmark positions
        # and returns the recognized gesture.
        gesture = self.hand_detector.get_gesture(lmList)

        # Print the recognized gesture in the terminal.
        print("gesture: ", gesture)


# ============================================================
# 7. MAIN FUNCTION
# ============================================================

def main():

    # Print a separator in the terminal.
    print('----------------------')

    # Initialize the ROS 2 Python client library.
    rclpy.init()

    # Create the MediaPipe hand detection ROS 2 node.
    mediapipe_detect = MediapipeDetectNode(
        'MediapipeDetect_node'
    )

    # Keep the node running.
    #
    # ROS 2 continuously processes incoming camera messages.
    # Each new image triggers callback(), which processes the image
    # and performs hand detection.
    rclpy.spin(mediapipe_detect)


# ============================================================
# 8. RUN THE PROGRAM
# ============================================================

# Execute main() when this Python file is run directly.
if __name__ == '__main__':
    main()
