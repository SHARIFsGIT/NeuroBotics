
# Import CvBridge to convert ROS 2 Image messages into OpenCV images.
from cv_bridge import CvBridge

# Import OpenCV for image processing and displaying images.
import cv2

# Import the Node class, which is the base class for ROS 2 nodes.
from rclpy.node import Node

# Import the ROS 2 Python client library.
import rclpy

# Import the Image message type used by ROS 2 camera topics.
from sensor_msgs.msg import Image


# Supported depth image encodings:
# 16UC1 = 16-bit unsigned integer depth image.
# 32FC1 = 32-bit floating-point depth image.
encoding = ['16UC1', '32FC1']


# Create a ROS 2 node for displaying a colourized depth image.
class ImagetNode(Node):

    def __init__(self, name):

        # Initialize the parent Node class with the given node name.
        super().__init__(name)

        # Subscribe to the camera's depth image topic.
        # Whenever a new depth image arrives, get_DepthImgCallBack() is called.
        # The value 100 is the subscription queue size.
        self.sub_depth = self.create_subscription(
            Image,
            "/camera/depth/image_raw",
            self.get_DepthImgCallBack,
            100
        )

        # Create a CvBridge object.
        # It converts ROS 2 image messages into OpenCV image formats.
        self.depth_bridge = CvBridge()

    # This callback function runs whenever a new depth image is received.
    def get_DepthImgCallBack(self, depth_frame):

        # Convert the ROS 2 depth image message into an OpenCV image.
        # encoding[1] means '32FC1' (32-bit floating-point, single-channel).
        depth_image = self.depth_bridge.imgmsg_to_cv2(
            depth_frame,
            encoding[1]
        )

        # Convert the depth image into an 8-bit image and apply a colour map.
        #
        # convertScaleAbs():
        #   - Converts the image into an 8-bit format.
        #   - alpha=0.35 controls the image brightness/intensity.
        #
        # COLORMAP_JET:
        #   - Applies a colour gradient to make depth differences easier to see.
        #   - Different depth values are represented by different colours.
        depth_to_color_image = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.35),
            cv2.COLORMAP_JET
        )

        # Process OpenCV window events.
        # The value 1 means OpenCV waits approximately 1 millisecond.
        key = cv2.waitKey(1)

        # Display the colourized depth image in a window named "result_image".
        cv2.imshow("result_image", depth_to_color_image)


# Main function: the starting point of the ROS 2 program.
def main():

    # Print a separator in the terminal.
    print('----------------------')

    # Initialize the ROS 2 Python client library.
    rclpy.init()

    # Create an instance of our depth image processing node.
    depth_color_image = ImagetNode('Depth_Color_Image_node')

    # Keep the node running and process incoming ROS 2 messages.
    # The callback executes whenever a depth image is received.
    rclpy.spin(depth_color_image)

    # These cleanup commands run after the node stops spinning.
    depth_color_image.destroy_node()
    rclpy.shutdown()


# Execute main() when this Python file is run directly.
if __name__ == '__main__':
    main()
