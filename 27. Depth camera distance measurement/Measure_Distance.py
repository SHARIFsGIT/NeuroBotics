
# Import CvBridge to convert ROS 2 Image messages into OpenCV images.
from cv_bridge import CvBridge

# Import OpenCV for image processing, mouse events, and displaying images.
import cv2

# Import the Node class to create a ROS 2 node.
from rclpy.node import Node

# Import the ROS 2 Python client library.
import rclpy

# Import the Image message type used by camera topics.
from sensor_msgs.msg import Image

# Import NumPy for numerical operations and image data conversion.
import numpy as np


# Supported depth image encodings:
# 16UC1 = 16-bit unsigned integer, single-channel depth image.
# 32FC1 = 32-bit floating-point, single-channel depth image.
encoding = ['16UC1', '32FC1']


# Create a ROS 2 node for displaying and measuring depth images.
class ImagetNode(Node):

    def __init__(self, name):

        # Initialize the parent ROS 2 Node class.
        super().__init__(name)

        # Subscribe to the camera's depth image topic.
        # The callback function runs whenever a new depth image arrives.
        self.sub_depth = self.create_subscription(
            Image,
            "/camera/depth/image_raw",
            self.get_DepthImgCallBack,
            100
        )

        # Create a CvBridge object to convert ROS images into OpenCV images.
        self.depth_bridge = CvBridge()

        # Name of the OpenCV window used to display the depth image.
        self.window_name = "result_image"

        # Initial Y coordinate of the selected pixel.
        # 240 represents the vertical position.
        self.y = 240

        # Initial X coordinate of the selected pixel.
        # 320 represents the horizontal position.
        self.x = 320

    # This function handles mouse events inside the OpenCV window.
    def click_callback(self, event, x, y, flags, params):

        # event == 1 represents a left mouse button click.
        if event == 1:

            # Save the horizontal coordinate of the clicked pixel.
            self.x = x

            # Save the vertical coordinate of the clicked pixel.
            self.y = y

    # This callback function processes every incoming depth image.
    def get_DepthImgCallBack(self, depth_frame):

        # Convert the ROS 2 depth image message into an OpenCV image.
        # encoding[1] selects '32FC1'.
        depth_image = self.depth_bridge.imgmsg_to_cv2(
            depth_frame,
            encoding[1]
        )

        # Convert the depth image into an 8-bit image and apply the JET colour map.
        # alpha=0.45 controls the intensity scaling of the depth values.
        depth_to_color_image = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.45),
            cv2.COLORMAP_JET
        )

        # Convert the depth image into NumPy float32 format.
        # This allows us to read the depth value at a specific pixel.
        depth_image_info = depth_image.astype(np.float32)

        # Read the depth value at the currently selected pixel.
        # NumPy uses [row, column], so the order is [y, x].
        dist = depth_image_info[self.y, self.x]

        # Round the depth value to three decimal places.
        dist = round(dist, 3)

        # Convert the depth value into a string for displaying on the image.
        # The original code labels the value in millimetres.
        dist = 'dist: ' + str(dist) + 'mm'

        # Display the selected pixel's depth value on the image.
        # Parameters:
        #   depth_to_color_image = image on which the text is drawn.
        #   dist                 = text to display.
        #   (10, 40)             = text position.
        #   FONT_HERSHEY_SIMPLEX = font type.
        #   1.0                  = font size.
        #   (0, 0, 255)          = red colour in BGR format.
        #   2                    = text thickness.
        cv2.putText(
            depth_to_color_image,
            dist,
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            2
        )

        # Register the mouse callback function for the display window.
        # When the user clicks inside the window, click_callback() is called.
        cv2.setMouseCallback(
            self.window_name,
            self.click_callback
        )

        # Draw a black circle at the currently selected pixel.
        # (self.x, self.y) = circle centre.
        # 1                  = circle radius.
        # (0, 0, 0)          = black colour.
        # 10                 = line thickness.
        cv2.circle(
            depth_to_color_image,
            (self.x, self.y),
            1,
            (0, 0, 0),
            10
        )

        # Display the colourized depth image.
        cv2.imshow(
            "result_image",
            depth_to_color_image
        )

        # Process OpenCV window events.
        # This also allows mouse clicks to be detected.
        key = cv2.waitKey(1)


# Main function: the starting point of the ROS 2 program.
def main():

    # Print a separator in the terminal.
    print('----------------------')

    # Initialize ROS 2.
    rclpy.init()

    # Create the depth image processing node.
    depth_color_image = ImagetNode('Depth_Color_Image_node')

    # Keep the node running and process incoming depth images.
    rclpy.spin(depth_color_image)

    # Clean up the node when ROS 2 stops spinning.
    depth_color_image.destroy_node()

    # Shut down the ROS 2 client library.
    rclpy.shutdown()


# Run main() when this Python file is executed directly.
if __name__ == '__main__':
    main()
