
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ============================================================
# IMPORT LIBRARIES
# ============================================================

# OpenCV: Image processing, drawing bounding boxes and displaying results.
import cv2

# NumPy: Numerical calculations and image array operations.
import numpy as np

# OrderedDict: Stores TensorRT input/output bindings in an ordered dictionary.
from collections import OrderedDict, namedtuple

# Time: Used for measuring inference time and adding delays.
import time

# PyTorch: Used for GPU tensor operations and CUDA acceleration.
import torch

# Sys: Allows us to add custom directories to Python's module search path.
import sys

# Add the YOLOv8 source directory to Python's module search path.
sys.path.append(
    '/home/jetson/yahboomcar_ws/src/yahboom_yolov8/yahboom_yolov8/yolov8'
)

# Import the custom TensorRT tracking module.
# This module is responsible for updating object tracking information.
import tracker_trt

# Import YOLO utilities:
# non_max_suppression removes duplicate overlapping detections.
# scale_boxes converts bounding box coordinates to the original image size.
from ultralytics.utils.ops import non_max_suppression, scale_boxes

# TensorRT: NVIDIA's inference engine for accelerating deep learning models.
import tensorrt as trt

# ROS 2 Python client library.
import rclpy

# Base class for creating ROS 2 nodes.
from rclpy.node import Node

# ROS 2 image message type.
from sensor_msgs.msg import Image

# ROS 2 integer message type.
from std_msgs.msg import Int16

# CvBridge: Converts between ROS images and OpenCV images.
from cv_bridge import CvBridge

# Import Yahboom robot movement and control utilities.
from yahboom_yolov8.Robot_Move import *

# Import common functions, including PID controllers and image utilities.
from yahboom_yolov8.common import *

# Twist: ROS message used to control robot linear and angular velocity.
from geometry_msgs.msg import Twist

# ArmJoints: Custom ROS message for controlling the six robotic arm joints.
from arm_msgs.msg import ArmJoints

# LaserScan: ROS message containing laser scanner distance measurements.
from sensor_msgs.msg import LaserScan

# Math: Used for angle conversions and mathematical calculations.
import math

# OS: Used to execute a ROS 2 command from the operating system.
import os


# ============================================================
# GLOBAL VARIABLES
# ============================================================

# Conversion factor from radians to degrees.
RAD2DEG = 180 / math.pi

# Supported depth image encodings.
# 16UC1: 16-bit unsigned integer depth image.
# 32FC1: 32-bit floating-point depth image.
encoding = ['16UC1', '32FC1']


# COCO dataset class names.
# YOLO uses these names to identify detected objects.
names = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
    'train', 'truck', 'boat', 'traffic light', 'fire hydrant',
    'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog',
    'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
    'giraffe', 'backpack', 'umbrella', 'handbag', 'tie',
    'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
    'kite', 'baseball bat', 'baseball glove', 'skateboard',
    'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
    'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
    'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog',
    'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant',
    'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
    'remote', 'keyboard', 'cell phone', 'microwave', 'oven',
    'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase',
    'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]

# Generate a random RGB color for every object class.
# These colors can be used to draw different detection results.
colors = [
    [np.random.randint(0, 255) for _ in range(3)]
    for _ in names
]

print("--------------------------------------------")


# ============================================================
# IMAGE PREPROCESSING: LETTERBOX
# ============================================================

def letterbox(
    im,
    new_shape=(640, 640),
    color=(114, 114, 114),
    auto=False,
    scaleup=True,
    stride=32
):

    # Get the original image dimensions.
    # shape[0] = image height.
    # shape[1] = image width.
    shape = im.shape[:2]

    # If new_shape is a single integer, create a square image size.
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Calculate the scaling ratio.
    # The smaller ratio is selected to ensure that the image fits
    # inside the target dimensions without changing its aspect ratio.
    r = min(
        new_shape[0] / shape[0],
        new_shape[1] / shape[1]
    )

    # If scaleup is False, only allow the image to become smaller.
    if not scaleup:
        r = min(r, 1.0)

    # Calculate the new image dimensions after resizing.
    new_unpad = (
        int(round(shape[1] * r)),
        int(round(shape[0] * r))
    )

    # Calculate the remaining width and height.
    # These values represent the padding required to reach new_shape.
    dw = new_shape[1] - new_unpad[0]
    dh = new_shape[0] - new_unpad[1]

    # If automatic padding is enabled, adjust padding
    # according to the model's stride.
    if auto:
        dw, dh = np.mod(dw, stride), np.mod(dh, stride)

    # Divide the padding equally between both sides.
    dw /= 2
    dh /= 2

    # Resize the image if its dimensions are different from the target.
    if shape[::-1] != new_unpad:
        im = cv2.resize(
            im,
            new_unpad,
            interpolation=cv2.INTER_LINEAR
        )

    # Calculate the padding for the top, bottom, left and right.
    top = int(round(dh - 0.1))
    bottom = int(round(dh + 0.1))
    left = int(round(dw - 0.1))
    right = int(round(dw + 0.1))

    # Add borders to make the image reach the required dimensions.
    im = cv2.copyMakeBorder(
        im,
        top,
        bottom,
        left,
        right,
        cv2.BORDER_CONSTANT,
        value=color
    )

    # Return:
    # im: Resized and padded image.
    # r: Scaling ratio.
    # (dw, dh): Horizontal and vertical padding.
    return im, r, (dw, dh)


# ============================================================
# TENSORRT YOLOv8 ROS 2 NODE
# ============================================================

class TRT_engine(Node):

    def __init__(
        self,
        weight,
        thres=0.60,
        size=640,
        video_path='',
        batch_size=3
    ):

        # Initialize the ROS 2 node.
        super().__init__('yolov8_node')

        # Store the video path.
        # The current implementation does not directly use this variable.
        self.video_path = video_path

        # Input image size for YOLO inference.
        self.imgsz = size

        # Path to the TensorRT engine file.
        self.weight = weight

        # IoU threshold used during non-maximum suppression.
        self.iou_thres = thres

        # Number of images processed together in one inference batch.
        self.batch_size = batch_size

        # Select the first NVIDIA CUDA GPU.
        self.device = torch.device('cuda:0')

        # Load and initialize the TensorRT engine.
        self.init_engine()

        # Stores the latest incoming ROS image message.
        self.frame = None

        # CvBridge for converting OpenCV images into ROS images.
        self.rgb_bridge = CvBridge()

        # CvBridge for converting ROS images into OpenCV images.
        self.msg2img_bridge = CvBridge()

        # ----------------------------------------------------
        # ROS 2 PUBLISHERS
        # ----------------------------------------------------

        # Publisher for controlling the six-joint robotic arm.
        # Topic: arm6_joints
        self.TargetAngle_pub = self.create_publisher(
            ArmJoints,
            "arm6_joints",
            10
        )

        # Publisher for images containing YOLO detection results.
        # Topic: detect_image
        self.yolov8_img_pub = self.create_publisher(
            Image,
            "detect_image",
            1
        )

        # Publisher for robot movement commands.
        # Topic: /cmd_vel
        self.cmd_pub = self.create_publisher(
            Twist,
            "/cmd_vel",
            1
        )

        # ----------------------------------------------------
        # ROS 2 SUBSCRIBERS
        # ----------------------------------------------------

        # Subscribe to the Orbbec RGB camera.
        self.sub_rgb = self.create_subscription(
            Image,
            "/camera/color/image_raw",
            self.get_RGBImageCallBack,
            1
        )

        # Subscribe to the laser scanner.
        self.sub_laser = self.create_subscription(
            LaserScan,
            "/scan",
            self.registerScan,
            1
        )

        # Store the tracking ID selected by another ROS 2 node.
        self.trackered_id = None

        # Subscribe to the selected tracking ID.
        # Topic: /tracker_id
        self.sub_t_id = self.create_subscription(
            Int16,
            "/tracker_id",
            self.get_IDCallBack,
            100
        )

        # Create a Twist message for robot movement.
        self.vel = Twist()

        # PID parameters for controlling the robot's angular movement.
        self.angular_PID = (0.5, 0.0, 0.3)

        # Create a linear PID controller.
        # It will be used to adjust the robot's distance from an object.
        self.lin_pid = SinglePID(0.5, 0.0, 0.1)

        # Create an angular PID controller.
        # The PID parameters are divided by 100 before being passed in.
        self.angular_pid = simplePID(
            self.angular_PID[0] / 100.0,
            self.angular_PID[1] / 100.0,
            self.angular_PID[2] / 100.0
        )

        # Indicates whether the selected object has been detected.
        self.found = False

        # Indicates whether joystick control is active.
        self.joy_ctrl = False

        # Initial positions of the six robotic arm joints.
        self.init_joints = [90, 178, 0, 0, 90, 90]

        # Wait until another ROS 2 node subscribes to arm6_joints.
        # This helps ensure that the arm controller is available
        # before sending the initial joint positions.
        while not self.TargetAngle_pub.get_subscription_count():

            # Publish the initial robotic arm position.
            self.pubSix_Arm(self.init_joints)

            # Wait for 0.1 seconds before checking again.
            time.sleep(0.1)

        # Publish the initial arm position once more.
        self.pubSix_Arm(self.init_joints)

        # Store preprocessed images for batch inference.
        self.img_list = []

        # Store original camera frames for drawing detection results.
        self.original_frames = []

        # Laser scanner angle range.
        # Only laser measurements within +/- 5 degrees are considered.
        self.LaserAngle = 5

        # Placeholder for depth image data.
        self.depth_image_info = []

        # CvBridge for depth image conversion.
        # It is not used elsewhere in the supplied code.
        self.depth_bridge = CvBridge()

        # Indicates whether the robot has completed its rotation
        # toward the selected object.
        self.rotation_done = False

        # Desired distance from the selected object, in meters.
        self.ResponseDist = 1.2

    # ========================================================
    # STOP ROBOT
    # ========================================================

    def exit_pro(self):

        # Construct a ROS 2 command that publishes one zero-velocity message.
        cmd1 = "ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "

        # Set all linear and angular velocity components to zero.
        cmd2 = '''"{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"'''

        # Combine the command strings.
        cmd = cmd1 + cmd2

        # Execute the command through the operating system.
        os.system(cmd)

    # ========================================================
    # LASER SCANNER CALLBACK
    # ========================================================

    def registerScan(self, scan_data):

        # Confirm that the incoming message is a LaserScan message.
        if not isinstance(scan_data, LaserScan):
            return

        # Convert the laser ranges into a NumPy array.
        # Each element represents a measured distance.
        ranges = np.array(scan_data.ranges)

        # Store distances that fall within the selected angle range.
        minDistList = []

        # Store the corresponding angles for those distances.
        minDistIDList = []

        # Examine every laser measurement.
        for i in range(len(ranges)):

            # Calculate the angle of the current laser measurement.
            # Convert the angle from radians to degrees.
            angle = (
                scan_data.angle_min
                + scan_data.angle_increment * i
            ) * RAD2DEG

            # Only consider measurements within +/- LaserAngle degrees.
            # Ignore measurements equal to zero.
            if abs(angle) < self.LaserAngle and ranges[i] != 0.0:

                # Store the measured distance.
                minDistList.append(ranges[i])

                # Store the angle associated with that distance.
                minDistIDList.append(angle)

        # If no valid measurements were found, exit the callback.
        if len(minDistList) == 0:
            return

        # Find the smallest distance in the selected laser angle range.
        minDist = min(minDistList)

        # Find the angle associated with the smallest distance.
        minDistID = minDistIDList[minDistList.index(minDist)]

        # Print the closest measured distance.
        print("minDist: ", minDist)

        # Only adjust the robot's distance after its rotation is complete.
        if self.rotation_done == True:

            # Check whether the measured distance is close enough
            # to the desired distance.
            if abs(minDist - self.ResponseDist) < 0.2:

                # Treat the measured distance as the target distance.
                minDist = self.ResponseDist

                # Publish zero velocity to stop the robot.
                self.cmd_pub.publish(Twist())

            else:

                # Ignore infinite laser readings.
                if not math.isinf(minDist):

                    # Calculate the linear velocity using the PID controller.
                    #
                    # The negative sign determines the direction
                    # of the correction according to the controller setup.
                    linear_x = -self.lin_pid.pid_compute(
                        self.ResponseDist,
                        minDist
                    )

                    print("linear_x: ", linear_x)

                    # Set the robot's forward/backward velocity.
                    self.vel.linear.x = linear_x

                    # Publish the velocity command.
                    self.cmd_pub.publish(self.vel)

    # ========================================================
    # ROBOTIC ARM CONTROL
    # ========================================================

    def pubSix_Arm(self, joints, id=6, angle=180.0, runtime=2000):

        # Create a new ArmJoints message.
        arm_joint = ArmJoints()

        # Assign the six joint angles.
        arm_joint.joint1 = joints[0]
        arm_joint.joint2 = joints[1]
        arm_joint.joint3 = joints[2]
        arm_joint.joint4 = joints[3]
        arm_joint.joint5 = joints[4]
        arm_joint.joint6 = joints[5]

        # Set the movement duration in milliseconds.
        arm_joint.time = runtime

        # Publish the joint command.
        self.TargetAngle_pub.publish(arm_joint)

    # ========================================================
    # TRACKING ID CALLBACK
    # ========================================================

    def get_IDCallBack(self, msg):

        # Read the tracking ID from the incoming Int16 message.
        # This ID identifies which detected object the robot should follow.
        self.trackered_id = msg.data

    # ========================================================
    # RGB CAMERA CALLBACK
    # ========================================================

    def get_RGBImageCallBack(self, rgb_msg):

        # Store the latest incoming camera image message.
        self.frame = rgb_msg

        # Process the camera image.
        self.process()

    # ========================================================
    # INITIALIZE TENSORRT ENGINE
    # ========================================================

    def init_engine(self):

        # Create a named tuple to store TensorRT binding information.
        #
        # name: Tensor name.
        # dtype: Tensor data type.
        # shape: Tensor dimensions.
        # data: PyTorch tensor containing the data.
        # ptr: GPU memory address.
        self.Binding = namedtuple(
            'Binding',
            ('name', 'dtype', 'shape', 'data', 'ptr')
        )

        # Create a TensorRT logger.
        # INFO displays informational messages from TensorRT.
        self.logger = trt.Logger(trt.Logger.INFO)

        # Initialize TensorRT plugins.
        # Some models require these plugins to execute correctly.
        trt.init_libnvinfer_plugins(
            self.logger,
            namespace=""
        )

        # Open the TensorRT engine file in binary read mode.
        #
        # Deserialize the file to load the optimized model into memory.
        with open(self.weight, 'rb') as self.f, trt.Runtime(self.logger) as self.runtime:

            self.model = self.runtime.deserialize_cuda_engine(
                self.f.read()
            )

        # OrderedDict stores all model input and output bindings.
        self.bindings = OrderedDict()

        # Loop through every input and output tensor in the engine.
        for index in range(self.model.num_io_tensors):

            # Get the tensor name.
            self.name = self.model.get_tensor_name(index)

            # Get the tensor's NumPy data type.
            self.dtype = trt.nptype(
                self.model.get_tensor_dtype(self.name)
            )

            # Get the tensor dimensions.
            self.shape = tuple(
                self.model.get_tensor_shape(self.name)
            )

            # Create an empty NumPy array with the correct shape and type.
            # Convert it into a PyTorch tensor and move it to the GPU.
            self.data = torch.from_numpy(
                np.empty(
                    self.shape,
                    dtype=np.dtype(self.dtype)
                )
            ).to(self.device)

            # Save the tensor information and GPU memory pointer.
            self.bindings[self.name] = self.Binding(
                self.name,
                self.dtype,
                self.shape,
                self.data,
                int(self.data.data_ptr())
            )

        # Create the TensorRT execution context.
        # The context is responsible for running model inference.
        self.context_ = self.model.create_execution_context()

        # Tell TensorRT where the GPU memory for each tensor is located.
        for name, binding in self.bindings.items():

            self.context_.set_tensor_address(
                name,
                binding.ptr
            )

    # ========================================================
    # TENSORRT INFERENCE
    # ========================================================

    def predict(self, imgs):

        # Copy the input image batch into the TensorRT input tensor.
        #
        # The engine is expected to have an input tensor named 'images'.
        self.bindings['images'].data.copy_(imgs)

        # Execute the TensorRT inference asynchronously on the CUDA stream.
        self.context_.execute_async_v3(
            torch.cuda.current_stream().cuda_stream
        )

        # Wait until GPU inference is complete.
        torch.cuda.synchronize()

        # Retrieve the output tensor.
        # The engine is expected to have an output tensor named 'output0'.
        outputs = self.bindings['output0'].data

        # Return the model predictions.
        return outputs

    # ========================================================
    # IMAGE PROCESSING AND OBJECT TRACKING
    # ========================================================

    def process(self):

        # Convert the ROS 2 camera image message into an OpenCV image.
        # The incoming image is interpreted as RGB.
        frame = self.msg2img_bridge.imgmsg_to_cv2(
            self.frame,
            "rgb8"
        )

        # ----------------------------------------------------
        # IMAGE PREPROCESSING
        # ----------------------------------------------------

        # Resize and normalize the camera image for YOLO inference.
        #
        # frame_tensor: Image tensor prepared for the GPU.
        # _: Original image returned by preprocess(), not used here.
        # dw: Horizontal padding.
        # dh: Vertical padding.
        frame_tensor, _, dw, dh = preprocess(
            frame,
            imgsz=self.imgsz
        )

        # Add the preprocessed image to the batch list.
        self.img_list.append(frame_tensor)

        # Save the original image for drawing detection results later.
        self.original_frames.append(frame)

        # ----------------------------------------------------
        # BATCH PROCESSING
        # ----------------------------------------------------

        # Run inference only after collecting the required number of frames.
        if len(self.img_list) == self.batch_size:

            # Combine individual image tensors into one batch.
            frames = torch.stack(
                self.img_list,
                0
            )

            # Record the start time of inference.
            t1 = time.perf_counter()

            # Run the TensorRT model.
            outputs = self.predict(frames)

            # Record the end time of inference.
            t2 = time.perf_counter()

            # Calculate the average inference time per image.
            infer_time = (t2 - t1) / self.batch_size

            # Apply Non-Maximum Suppression (NMS).
            #
            # NMS removes duplicate bounding boxes that overlap too much.
            #
            # 0.25: Confidence threshold.
            # self.iou_thres: IoU threshold.
            outputs = non_max_suppression(
                outputs,
                0.25,
                self.iou_thres,
                classes=None,
                agnostic=False
            )

            # ------------------------------------------------
            # PROCESS EVERY IMAGE IN THE BATCH
            # ------------------------------------------------

            for i in range(self.batch_size):

                # Record the start time of image post-processing.
                t3 = time.perf_counter()

                # Process detections and map bounding boxes
                # back to the original image coordinates.
                result, det_infos = post_process(
                    self.original_frames[i],
                    outputs[i],
                    frames
                )

                # Update the object tracker using the detected objects.
                #
                # det_infos contains the bounding box, class and confidence.
                # tracker_trt assigns tracking IDs to detected objects.
                list_bbox = tracker_trt.update(
                    det_infos,
                    frame
                )

                # Each tracking result contains:
                # x1, y1: Top-left bounding box coordinates.
                # x2, y2: Bottom-right bounding box coordinates.
                # cls: Object class name.
                # track_id: Unique tracking ID.
                for (x1, y1, x2, y2, cls, track_id) in list_bbox:

                    # Default bounding box color: Green.
                    color = [0, 255, 0]

                    # Draw a rectangle around the detected object.
                    cv2.rectangle(
                        result,
                        (int(x1), int(y1)),
                        (int(x2), int(y2)),
                        color,
                        2
                    )

                    # Display the object class and tracking ID.
                    cv2.putText(
                        result,
                        f'{cls} {track_id}',
                        (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2
                    )

                    # Check whether this object matches
                    # the tracking ID selected by the user.
                    if track_id == self.trackered_id:

                        # Mark the selected object as found.
                        self.found = True

                        # Change the selected object's color to red.
                        color = [0, 0, 255]

                        # Calculate the center of the selected object.
                        self.cx = (x1 + x2) / 2
                        self.cy = (y1 + y2) / 2

                        # Draw a circle at the center of the selected object.
                        cv2.circle(
                            result,
                            (int(self.cx), int(self.cy)),
                            5,
                            (255, 255, 0),
                            2
                        )

                        # Draw a red bounding box around the selected object.
                        cv2.rectangle(
                            result,
                            (int(x1), int(y1)),
                            (int(x2), int(y2)),
                            color,
                            2
                        )

                        # Display its class name and tracking ID.
                        cv2.putText(
                            result,
                            f'{cls} {track_id}',
                            (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            color,
                            2
                        )

                # ------------------------------------------------
                # CALCULATE FPS
                # ------------------------------------------------

                # Record the end time of image post-processing.
                t4 = time.perf_counter()

                # Calculate the approximate processing FPS.
                fps = 1 / (infer_time + t4 - t3)

                # Display FPS on the processed image.
                cv2.putText(
                    result,
                    f"{fps:.2f} FPS",
                    (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                # Convert the processed OpenCV image into a ROS 2 Image message.
                ros_image = self.rgb_bridge.cv2_to_imgmsg(
                    result,
                    encoding='rgb8'
                )

                # Publish the annotated image.
                self.yolov8_img_pub.publish(ros_image)

            # ------------------------------------------------
            # ROBOT OBJECT FOLLOWING CONTROL
            # ------------------------------------------------

            # If the selected object is detected and joystick control
            # is not active, the robot can automatically follow the object.
            if self.found == True and self.joy_ctrl == False:

                # Check whether the selected object is away from
                # the center of the camera image.
                #
                # The camera image is assumed to have a width of 640 pixels.
                # Its horizontal center is therefore 320 pixels.
                if abs(self.cx - 320) > 5:

                    # Calculate the required angular velocity.
                    #
                    # The PID controller compares:
                    # 320: Desired horizontal center.
                    # self.cx: Actual horizontal center of the object.
                    angular_z = self.angular_pid.compute(
                        320,
                        self.cx
                    )

                    # If the calculated angular velocity is very small,
                    # consider the robot aligned with the object.
                    if abs(angular_z) < 0.1:

                        # Set angular velocity to zero.
                        angular_z = 0.0

                        # Mark rotation as complete.
                        # The laser callback can now control distance.
                        self.rotation_done = True

                        # Update the angular velocity command.
                        self.vel.angular.z = angular_z

                        # Publish the command.
                        self.cmd_pub.publish(self.vel)

                    else:

                        # The robot is still rotating toward the object.
                        self.rotation_done = False

                        print("angular_z: ", angular_z)

                        # Set the angular velocity.
                        self.vel.angular.z = angular_z

                        # Publish the rotation command.
                        self.cmd_pub.publish(self.vel)

                else:

                    # If the object is already near the center,
                    # stop the robot's movement command.
                    self.cmd_pub.publish(Twist())

            else:

                # If the selected object is not found,
                # or joystick control is active, publish zero velocity.
                self.cmd_pub.publish(Twist())

            # ------------------------------------------------
            # CLEAR BATCH DATA
            # ------------------------------------------------

            # Empty the image tensor list for the next batch.
            self.img_list = []

            # Empty the original image list for the next batch.
            self.original_frames = []

            # Reset the detection flag for the next batch.
            self.found = False

        # The original code also contained a commented-out block
        # that would publish zero velocity when the batch was incomplete.


# ============================================================
# IMAGE PREPROCESSING FOR YOLOv8
# ============================================================

def preprocess(image, imgsz=640):

    # Resize the image to the YOLO input size while preserving
    # its original aspect ratio.
    #
    # The remaining space is filled with padding.
    img, ratio, (dw, dh) = letterbox(
        image,
        imgsz,
        stride=32,
        auto=False
    )

    # Convert the image from BGR to RGB.
    img = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2RGB
    )

    # Change image dimensions from:
    # Height x Width x Channels
    #
    # To:
    # Channels x Height x Width
    #
    # This is the tensor layout expected by the model.
    img = img.transpose((2, 0, 1))

    # Make the image array contiguous in memory.
    img = np.ascontiguousarray(img)

    # Convert the NumPy array into a PyTorch tensor
    # and move it to the NVIDIA GPU.
    img = torch.from_numpy(img).to(
        torch.device('cuda:0')
    ).float()

    # Normalize pixel values from 0-255 to 0-1.
    img /= 255.0

    # Return the preprocessed image and other information.
    return img, image, dw, dh


# ============================================================
# YOLO DETECTION POST-PROCESSING
# ============================================================

def post_process(img, det, frames):

    """
    Extract detected objects and their bounding box information.

    img:
        Original camera image.

    det:
        YOLO detection results after Non-Maximum Suppression.

    frames:
        Input image batch used by the YOLO model.
    """

    # This list stores the detection information for the tracker.
    detections = []

    # Check whether at least one object was detected.
    if len(det):

        # Convert bounding box coordinates from model input dimensions
        # back to the original image dimensions.
        #
        # frames.shape[2:] represents the model input height and width.
        # img.shape represents the original image dimensions.
        det[:, :4] = scale_boxes(
            frames.shape[2:],
            det[:, :4],
            img.shape
        ).round()

        # Process every detected object.
        #
        # reversed(det) processes detections in reverse order.
        for *xyxy, conf, cls in reversed(det):

            # Create a label containing the class name and confidence.
            label = f'{names[int(cls)]} {conf:.2f}'

            # Convert the detected class ID into an integer.
            cls_id = int(cls)

            # Get the class name using the class ID.
            cls1 = names[int(cls)]

            # Store detection information:
            #
            # x1, y1: Top-left corner.
            # x2, y2: Bottom-right corner.
            # cls1: Object class name.
            # conf.item(): Detection confidence.
            #
            # The tracker uses this information to identify
            # objects across multiple frames.
            detections.append(
                (
                    int(xyxy[0]),
                    int(xyxy[1]),
                    int(xyxy[2]),
                    int(xyxy[3]),
                    cls1,
                    conf.item()
                )
            )

    # Return the original image and the detected objects.
    return img, detections


# ============================================================
# MAIN FUNCTION
# ============================================================

def main():

    # Initialize the ROS 2 communication system.
    rclpy.init()

    # Number of images processed together.
    # Here, batch_size is set to 1.
    batch_size = 1

    # Path to the optimized YOLOv8 TensorRT engine.
    trt_path = (
        "/home/jetson/yahboomcar_ws/src/yahboom_yolov8/"
        "yahboom_yolov8/yolov8/weights/yolov8s.trt"
    )

    # Create the TensorRT YOLOv8 ROS 2 node.
    trt_engine = TRT_engine(
        trt_path,
        batch_size=batch_size,
        thres=0.45,
        size=640,
        video_path=(
            "/home/jetson/yahboomcar_ws/src/yahboom_yolov8/"
            "yahboom_yolov8/yolov8/demo.mp4"
        )
    )

    try:

        # Keep the ROS 2 node running.
        # Process camera images, tracking IDs and laser measurements.
        rclpy.spin(trt_engine)

    except KeyboardInterrupt:

        # Handle Ctrl+C without displaying an unnecessary error.
        pass

    finally:

        # Stop the robot before shutting down.
        trt_engine.exit_pro()

        # Destroy the ROS 2 node.
        trt_engine.destroy_node()

        # Shut down ROS 2.
        rclpy.shutdown()


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

# Execute main() when this Python file is run directly.
if __name__ == '__main__':
    main()
