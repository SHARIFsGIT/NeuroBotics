
# ============================================================
# 1. IMPORT REQUIRED LIBRARIES
# ============================================================

# Import the ROS 2 Python client library.
import rclpy

# Import the Node class for creating a ROS 2 node.
from rclpy.node import Node

# Import the ROS 2 Image message type for receiving camera images.
from sensor_msgs.msg import Image

# Import Twist for controlling mobile robot movement.
# Twist contains linear and angular velocity values.
from geometry_msgs.msg import Twist

# Import ArmJoints for controlling the six robot arm joints.
from arm_msgs.msg import ArmJoints

# CvBridge converts ROS 2 Image messages into OpenCV images.
from cv_bridge import CvBridge

# OpenCV is used for image processing and displaying images.
import cv2

# NumPy is used for numerical operations and image processing.
import numpy as np

# Threading allows a function to execute in a separate thread.
import threading

# Time is used for adding delays.
# The original code uses time.sleep(), so this import is required.
import time


# Supported depth image encodings:
# 16UC1 = 16-bit unsigned integer depth image.
# 32FC1 = 32-bit floating-point depth image.
encoding = ['16UC1', '32FC1']


# ============================================================
# 2. CREATE THE EDGE DETECTION ROS 2 NODE
# ============================================================

class Edge_DetectionNode(Node):

    def __init__(self, name):

        # Initialize the parent ROS 2 Node class.
        super().__init__(name)

        # ----------------------------------------------------
        # INITIAL ROBOT ARM CONFIGURATION
        # ----------------------------------------------------

        # Initial positions for the six robot arm joints.
        #
        # joint1 = 90 degrees
        # joint2 = 120 degrees
        # joint3 = 0 degrees
        # joint4 = 0 degrees
        # joint5 = 90 degrees
        # joint6 = 90 degrees
        self.init_joints = [90, 120, 0, 0, 90, 90]

        # ----------------------------------------------------
        # MOBILE ROBOT VELOCITY PUBLISHER
        # ----------------------------------------------------

        # Create a publisher for controlling the mobile robot.
        #
        # Topic: /cmd_vel
        # Message type: Twist
        # Queue size: 1
        self.pub_vel = self.create_publisher(
            Twist,
            '/cmd_vel',
            1
        )

        # ----------------------------------------------------
        # ROBOT ARM JOINT PUBLISHER
        # ----------------------------------------------------

        # Create a publisher for sending target angles
        # to the six robot arm joints.
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
        # DEPTH CAMERA SUBSCRIBER
        # ----------------------------------------------------

        # Subscribe to the camera's depth image topic.
        #
        # Whenever a new depth image arrives,
        # get_DepthImageCallBack() is executed.
        #
        # Topic: /camera/depth/image_raw
        # Message type: Image
        # Queue size: 100
        self.sub_depth = self.create_subscription(
            Image,
            "/camera/depth/image_raw",
            self.get_DepthImageCallBack,
            100
        )

        # ----------------------------------------------------
        # WAIT FOR ROBOT ARM CONNECTION
        # ----------------------------------------------------

        # Check whether another ROS 2 node is subscribed
        # to the arm6_joints topic.
        #
        # If no subscriber is available, repeatedly publish
        # the initial arm position.
        while not self.TargetAngle_pub.get_subscription_count():

            # Send the initial arm joint positions.
            self.pubSix_Arm(self.init_joints)

            # Wait 0.1 seconds before checking again.
            time.sleep(0.1)

        # Once a subscriber is connected, publish the
        # initial arm joint positions again.
        self.pubSix_Arm(self.init_joints)

        # ----------------------------------------------------
        # MOBILE ROBOT MOVEMENT SETTINGS
        # ----------------------------------------------------

        # Set the forward movement speed.
        # The value is assigned to linear X velocity.
        self.lin_x = 0.1

        # Indicates whether joystick control is active.
        # This variable is initialized but not used elsewhere
        # in the current code.
        self.Joy_active = False

        # ----------------------------------------------------
        # DEPTH IMAGE CONVERSION
        # ----------------------------------------------------

        # Create a CvBridge object.
        # It converts ROS 2 depth image messages into OpenCV images.
        self.depth_bridge = CvBridge()

        # Movement state flag.
        #
        # False = robot is stopped.
        # True = robot is allowed to move forward.
        self.move_flag = False


    # ========================================================
    # 3. CALCULATE DISTANCE AND CONTROL ROBOT MOVEMENT
    # ========================================================

    def compute_dist(self, result_frame):

        # Resize the depth image to 640 x 480 pixels.
        #
        # This allows us to access the centre pixel
        # using coordinates (320, 240).
        frame = cv2.resize(
            result_frame,
            (640, 480)
        )

        # Convert the depth image into NumPy float32 format.
        # This makes it suitable for numerical calculations.
        depth_image_info = frame.astype(np.float32)

        # ----------------------------------------------------
        # CHECK WHETHER ROBOT MOVEMENT IS ENABLED
        # ----------------------------------------------------

        # If move_flag is True, the robot is allowed to move.
        if self.move_flag == True:

            # Read the depth value at the centre of the image.
            #
            # Pixel coordinates:
            #   X = 320 (horizontal centre)
            #   Y = 240 (vertical centre)
            #
            # Divide by 1000 to convert millimetres into metres,
            # assuming the camera depth values are in millimetres.
            #
            # Check whether the measured distance is greater than
            # 0.5 metres.
            if depth_image_info[240, 320] / 1000 > 0.5:

                # Stop the mobile robot by publishing zero velocity.
                self.pubVel(0, 0, 0)

                # Disable movement.
                self.move_flag = False

                # Print a stop message.
                print("Stop!!!")

            else:

                # If the measured distance is 0.5 metres or less,
                # publish a forward movement command.
                #
                # self.lin_x = 0.1
                # Y velocity = 0
                # Angular velocity = 0
                self.pubVel(
                    self.lin_x,
                    0,
                    0
                )

                # Print a movement message.
                print("Moving....")

        else:

            # If movement is disabled, keep the robot stopped.
            self.pubVel(0, 0, 0)

            # Ask the user to press SPACEBAR to enable movement.
            print(
                "Stop status now!Press the SPACEBAR to change the state."
            )


    # ========================================================
    # 4. DEPTH CAMERA CALLBACK
    # ========================================================

    # This function runs whenever a new depth image
    # is received from the camera.
    def get_DepthImageCallBack(self, msg):

        # Convert the ROS 2 depth image message into an OpenCV image.
        #
        # encoding[1] selects '32FC1':
        # 32-bit floating-point, single-channel depth image.
        depth_image = self.depth_bridge.imgmsg_to_cv2(
            msg,
            encoding[1]
        )

        # ----------------------------------------------------
        # RUN DISTANCE CALCULATION IN A SEPARATE THREAD
        # ----------------------------------------------------

        # Create a thread for processing the depth image
        # and calculating the robot movement command.
        #
        # target:
        #   The function that should execute.
        #
        # args:
        #   The depth image passed to that function.
        compute_ = threading.Thread(
            target=self.compute_dist,
            args=(depth_image,)
        )

        # Start the distance calculation thread.
        compute_.start()

        # Wait until the calculation thread finishes.
        #
        # join() ensures that the callback waits for
        # compute_dist() to complete before continuing.
        compute_.join()

        # ----------------------------------------------------
        # CHECK KEYBOARD INPUT
        # ----------------------------------------------------

        # Read keyboard input.
        # The value 10 means OpenCV waits approximately 10 milliseconds.
        key = cv2.waitKey(10)

        # ASCII value 32 represents the SPACEBAR.
        #
        # When SPACEBAR is pressed, enable robot movement.
        if key == 32:

            self.move_flag = True

        # ----------------------------------------------------
        # DISPLAY DEPTH IMAGE
        # ----------------------------------------------------

        # Display the original depth image in an OpenCV window.
        cv2.imshow(
            "frame",
            depth_image
        )


    # ========================================================
    # 5. PUBLISH MOBILE ROBOT VELOCITY
    # ========================================================

    def pubVel(self, vx, vy, vz):

        # Create a Twist message.
        vel = Twist()

        # Set forward/backward velocity.
        vel.linear.x = float(vx)

        # Set sideways velocity.
        vel.linear.y = float(vy)

        # Set rotational velocity around the Z-axis.
        vel.angular.z = float(vz)

        # Publish the velocity command to /cmd_vel.
        self.pub_vel.publish(vel)


    # ========================================================
    # 6. PUBLISH SIX ROBOT ARM JOINT ANGLES
    # ========================================================

    def pubSix_Arm(self, joints, id=6, angle=180.0, runtime=2000):

        # Create an ArmJoints message.
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

        # Set the movement duration in milliseconds.
        arm_joint.time = runtime

        # Publish the target joint positions.
        self.TargetAngle_pub.publish(arm_joint)


# ============================================================
# 7. MAIN FUNCTION
# ============================================================

def main():

    # Print a separator in the terminal.
    print('----------------------')

    # Initialize the ROS 2 Python client library.
    rclpy.init()

    # Create the Edge Detection ROS 2 node.
    edge_detect = Edge_DetectionNode(
        'Edge_Detection_node'
    )

    # Keep the node running and process incoming ROS 2 messages.
    #
    # Every new depth image triggers get_DepthImageCallBack().
    rclpy.spin(edge_detect)


# ============================================================
# 8. RUN THE PROGRAM
# ============================================================

# Execute main() when this Python file is run directly.
if __name__ == '__main__':
    main()
