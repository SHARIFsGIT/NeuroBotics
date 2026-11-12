
# ============================================================
# 1. IMPORT REQUIRED ROS 2 LIBRARIES
# ============================================================

# Main class used to create a ROS 2 launch description.
from launch import LaunchDescription

# DeclareLaunchArgument allows users to configure camera
# settings when starting the launch file.
from launch.actions import DeclareLaunchArgument

# LaunchConfiguration reads values passed through launch arguments.
from launch.substitutions import LaunchConfiguration

# PushRosNamespace adds a namespace to nodes started inside a group.
from launch_ros.actions import PushRosNamespace

# GroupAction groups multiple launch actions together.
from launch.actions import GroupAction

# ComposableNodeContainer creates a container that can run
# multiple ROS 2 components in the same process.
from launch_ros.actions import ComposableNodeContainer

# ComposableNode describes a ROS 2 component that can be loaded
# into a component container.
from launch_ros.descriptions import ComposableNode

# Node starts a normal ROS 2 node.
from launch_ros.actions import Node

# os provides access to operating system environment variables.
import os


# ============================================================
# 2. MAIN LAUNCH FUNCTION
# ============================================================

def generate_launch_description():

    # ========================================================
    # 3. DECLARE CAMERA CONFIGURATION ARGUMENTS
    # ========================================================

    # This list contains all configurable camera parameters.
    #
    # Each DeclareLaunchArgument creates an argument that
    # can be changed when starting the launch file.
    #
    # Example:
    # ros2 launch PACKAGE camera.launch.py color_fps:=30
    args = [

        # ----------------------------------------------------
        # 3.1 CAMERA IDENTIFICATION
        # ----------------------------------------------------

        # Namespace assigned to the camera.
        #
        # Default:
        # camera
        #
        # Camera topics may appear under:
        # /camera/color/image_raw
        # /camera/depth/image_raw
        DeclareLaunchArgument(
            'camera_name',
            default_value='camera'
        ),

        # Enable or disable depth registration.
        #
        # Registration aligns depth information with the
        # color camera image.
        #
        # Default: false
        DeclareLaunchArgument(
            'depth_registration',
            default_value='false'
        ),

        # Camera serial number.
        #
        # Useful when multiple cameras are connected.
        # An empty value means no serial number is specified.
        DeclareLaunchArgument(
            'serial_number',
            default_value=''
        ),

        # USB port used by the camera.
        #
        # An empty value means the USB port is not specified.
        DeclareLaunchArgument(
            'usb_port',
            default_value=''
        ),

        # Camera device number.
        #
        # Default device number: 1
        DeclareLaunchArgument(
            'device_num',
            default_value='1'
        ),

        # USB vendor ID of the camera.
        DeclareLaunchArgument(
            'vendor_id',
            default_value='0x2bc5'
        ),

        # USB product ID of the camera.
        #
        # An empty value means no product ID is specified.
        DeclareLaunchArgument(
            'product_id',
            default_value=''
        ),

        # ----------------------------------------------------
        # 3.2 POINT CLOUD SETTINGS
        # ----------------------------------------------------

        # Enable or disable point cloud publishing.
        #
        # A point cloud represents 3D information
        # using many individual points.
        #
        # Default: true
        DeclareLaunchArgument(
            'enable_point_cloud',
            default_value='true'
        ),

        # Enable or disable colored point cloud publishing.
        #
        # A colored point cloud contains both:
        # - 3D position information.
        # - RGB color information.
        DeclareLaunchArgument(
            'enable_colored_point_cloud',
            default_value='true'
        ),

        # Coordinate frame used for the point cloud.
        #
        # Empty means the driver uses its configured default.
        DeclareLaunchArgument(
            'cloud_frame_id',
            default_value=''
        ),

        # Quality of Service setting for point cloud messages.
        #
        # QoS controls how ROS 2 publishes and delivers messages.
        DeclareLaunchArgument(
            'point_cloud_qos',
            default_value='default'
        ),

        # Delay before establishing the camera connection.
        #
        # Default value: 100
        DeclareLaunchArgument(
            'connection_delay',
            default_value='100'
        ),

        # ----------------------------------------------------
        # 3.3 RGB CAMERA IMAGE SETTINGS
        # ----------------------------------------------------

        # RGB image width in pixels.
        DeclareLaunchArgument(
            'color_width',
            default_value='640'
        ),

        # RGB image height in pixels.
        DeclareLaunchArgument(
            'color_height',
            default_value='480'
        ),

        # RGB camera frame rate.
        #
        # Default: 30 frames per second.
        DeclareLaunchArgument(
            'color_fps',
            default_value='30'
        ),

        # RGB image encoding or format.
        #
        # Default: MJPG
        DeclareLaunchArgument(
            'color_format',
            default_value='MJPG'
        ),

        # Enable or disable RGB camera streaming.
        DeclareLaunchArgument(
            'enable_color',
            default_value='true'
        ),

        # Flip the RGB image if required.
        #
        # false = Do not flip.
        DeclareLaunchArgument(
            'flip_color',
            default_value='false'
        ),

        # Quality of Service setting for RGB images.
        DeclareLaunchArgument(
            'color_qos',
            default_value='default'
        ),

        # QoS setting for RGB camera calibration information.
        DeclareLaunchArgument(
            'color_camera_info_qos',
            default_value='default'
        ),

        # ----------------------------------------------------
        # 3.4 RGB CAMERA EXPOSURE AND IMAGE QUALITY
        # ----------------------------------------------------

        # Automatically adjust RGB camera exposure.
        #
        # true = Automatic exposure.
        # false = Manual exposure.
        DeclareLaunchArgument(
            'enable_color_auto_exposure',
            default_value='true'
        ),

        # Manual RGB exposure value.
        #
        # -1 means use the driver/device default.
        DeclareLaunchArgument(
            'color_exposure',
            default_value='-1'
        ),

        # RGB camera gain.
        #
        # -1 means use the driver/device default.
        DeclareLaunchArgument(
            'color_gain',
            default_value='-1'
        ),

        # Automatically adjust RGB white balance.
        DeclareLaunchArgument(
            'enable_color_auto_white_balance',
            default_value='true'
        ),

        # Manual RGB white balance value.
        DeclareLaunchArgument(
            'color_white_balance',
            default_value='-1'
        ),

        # Maximum automatic exposure value.
        DeclareLaunchArgument(
            'color_ae_max_exposure',
            default_value='-1'
        ),

        # RGB image brightness.
        DeclareLaunchArgument(
            'color_brightness',
            default_value='-1'
        ),

        # RGB image sharpness.
        DeclareLaunchArgument(
            'color_sharpness',
            default_value='-1'
        ),

        # RGB image saturation.
        DeclareLaunchArgument(
            'color_saturation',
            default_value='-1'
        ),

        # RGB image contrast.
        DeclareLaunchArgument(
            'color_contrast',
            default_value='-1'
        ),

        # RGB image gamma.
        DeclareLaunchArgument(
            'color_gamma',
            default_value='-1'
        ),

        # RGB image hue.
        DeclareLaunchArgument(
            'color_hue',
            default_value='-1'
        ),

        # ----------------------------------------------------
        # 3.5 DEPTH CAMERA SETTINGS
        # ----------------------------------------------------

        # Depth image width in pixels.
        DeclareLaunchArgument(
            'depth_width',
            default_value='640'
        ),

        # Depth image height in pixels.
        DeclareLaunchArgument(
            'depth_height',
            default_value='400'
        ),

        # Depth camera frame rate.
        DeclareLaunchArgument(
            'depth_fps',
            default_value='10'
        ),

        # Depth image format.
        #
        # Default: Y11
        DeclareLaunchArgument(
            'depth_format',
            default_value='Y11'
        ),

        # Enable or disable depth image streaming.
        DeclareLaunchArgument(
            'enable_depth',
            default_value='true'
        ),

        # Flip the depth image if required.
        DeclareLaunchArgument(
            'flip_depth',
            default_value='false'
        ),

        # QoS setting for depth image messages.
        DeclareLaunchArgument(
            'depth_qos',
            default_value='default'
        ),

        # QoS setting for depth camera calibration information.
        DeclareLaunchArgument(
            'depth_camera_info_qos',
            default_value='default'
        ),

        # Configuration file for the depth filter.
        #
        # Example mentioned in the original code:
        # /config/depthfilter/Openni_device.json
        #
        # Empty means no custom configuration path is supplied.
        DeclareLaunchArgument(
            'depth_filter_config',
            default_value=''
        ),

        # ----------------------------------------------------
        # 3.6 INFRARED CAMERA SETTINGS
        # ----------------------------------------------------

        # Infrared image width.
        DeclareLaunchArgument(
            'ir_width',
            default_value='640'
        ),

        # Infrared image height.
        DeclareLaunchArgument(
            'ir_height',
            default_value='400'
        ),

        # Infrared camera frame rate.
        DeclareLaunchArgument(
            'ir_fps',
            default_value='10'
        ),

        # Infrared image format.
        DeclareLaunchArgument(
            'ir_format',
            default_value='Y10'
        ),

        # Enable or disable infrared image streaming.
        DeclareLaunchArgument(
            'enable_ir',
            default_value='true'
        ),

        # Flip the infrared image if required.
        DeclareLaunchArgument(
            'flip_ir',
            default_value='false'
        ),

        # QoS setting for infrared image messages.
        DeclareLaunchArgument(
            'ir_qos',
            default_value='default'
        ),

        # QoS setting for infrared camera calibration information.
        DeclareLaunchArgument(
            'ir_camera_info_qos',
            default_value='default'
        ),

        # Automatically adjust infrared camera exposure.
        DeclareLaunchArgument(
            'enable_ir_auto_exposure',
            default_value='true'
        ),

        # Manual infrared exposure.
        DeclareLaunchArgument(
            'ir_exposure',
            default_value='-1'
        ),

        # Infrared camera gain.
        DeclareLaunchArgument(
            'ir_gain',
            default_value='-1'
        ),

        # ----------------------------------------------------
        # 3.7 TF AND CAMERA CALIBRATION SETTINGS
        # ----------------------------------------------------

        # Enable or disable publishing TF transforms.
        #
        # TF describes the relationships between coordinate frames.
        #
        # Default: true
        DeclareLaunchArgument(
            'publish_tf',
            default_value='true'
        ),

        # Rate at which TF transforms are published.
        #
        # Default: 0.0
        DeclareLaunchArgument(
            'tf_publish_rate',
            default_value='0.0'
        ),

        # URL of the infrared camera calibration file.
        DeclareLaunchArgument(
            'ir_info_url',
            default_value=''
        ),

        # URL of the RGB camera calibration file.
        DeclareLaunchArgument(
            'color_info_url',
            default_value=''
        ),

        # Logging level for the camera driver.
        #
        # Default: none
        DeclareLaunchArgument(
            'log_level',
            default_value='none'
        ),

        # Enable or disable publishing camera extrinsic information.
        #
        # Extrinsic information describes the spatial relationship
        # between different camera coordinate systems.
        DeclareLaunchArgument(
            'enable_publish_extrinsic',
            default_value='false'
        ),

        # ----------------------------------------------------
        # 3.8 DEPTH FILTER SETTINGS
        # ----------------------------------------------------

        # Enable or disable the software depth filter.
        DeclareLaunchArgument(
            'enable_soft_filter',
            default_value='true'
        ),

        # Enable or disable LDP.
        #
        # LDP is a camera-driver-specific setting.
        DeclareLaunchArgument(
            'enable_ldp',
            default_value='true'
        ),

        # Maximum depth difference used by the software filter.
        DeclareLaunchArgument(
            'soft_filter_max_diff',
            default_value='-1'
        ),

        # Speckle filter size.
        #
        # Speckles are small isolated noise regions
        # in a depth image.
        DeclareLaunchArgument(
            'soft_filter_speckle_size',
            default_value='-1'
        ),

        # ----------------------------------------------------
        # 3.9 POINT CLOUD AND TIMING SETTINGS
        # ----------------------------------------------------

        # Enable or disable ordered point cloud output.
        DeclareLaunchArgument(
            'ordered_pc',
            default_value='false'
        ),

        # Enable or disable hardware timestamps.
        DeclareLaunchArgument(
            'use_hardware_time',
            default_value='false'
        ),

        # Enable or disable depth scale configuration.
        DeclareLaunchArgument(
            'enable_depth_scale',
            default_value='true'
        ),

        # Depth-to-color alignment mode.
        #
        # Default: HW
        DeclareLaunchArgument(
            'align_mode',
            default_value='HW'
        ),

        # Infrared laser energy level.
        DeclareLaunchArgument(
            'laser_energy_level',
            default_value='-1'
        ),

        # Enable or disable the camera heartbeat.
        DeclareLaunchArgument(
            'enable_heartbeat',
            default_value='false'
        ),
    ]

    # ========================================================
    # 4. PREPARE NODE PARAMETERS
    # ========================================================

    # Convert every declared launch argument into a ROS 2 parameter.
    #
    # For example:
    #
    # color_width -> {'color_width': LaunchConfiguration('color_width')}
    #
    # This allows the camera driver to receive the values
    # provided when launching the file.
    parameters = [
        {
            arg.name: LaunchConfiguration(arg.name)
        }
        for arg in args
    ]

    # ========================================================
    # 5. CHECK THE ROS 2 DISTRIBUTION
    # ========================================================

    # Read the ROS_DISTRO environment variable.
    #
    # Examples:
    # ROS_DISTRO=foxy
    # ROS_DISTRO=humble
    # ROS_DISTRO=iron
    #
    # The camera driver uses a different startup method
    # depending on the ROS 2 distribution.
    ros_distro = os.environ["ROS_DISTRO"]

    # ========================================================
    # 6. START CAMERA USING A NORMAL NODE (ROS 2 FOXY)
    # ========================================================

    # ROS 2 Foxy uses a normal ROS 2 node in this launch file.
    if ros_distro == "foxy":

        # Return the launch description for Foxy.
        return LaunchDescription(

            # First register all camera configuration arguments.
            args
            +
            [

                # Start the Orbbec camera node.
                Node(

                    # Package containing the camera driver.
                    package="orbbec_camera",

                    # Camera driver executable.
                    executable="orbbec_camera_node",

                    # Name assigned to the camera node.
                    name="ob_camera_node",

                    # Use the camera_name launch argument as its namespace.
                    #
                    # Default namespace:
                    # /camera
                    namespace=LaunchConfiguration("camera_name"),

                    # Pass all camera configuration parameters.
                    parameters=parameters,

                    # The original code leaves terminal output disabled.
                    # You can uncomment this if you want to display it.
                    # output="screen",
                )
            ]
        )

    # ========================================================
    # 7. START CAMERA USING A COMPOSABLE NODE
    #    (OTHER ROS 2 DISTRIBUTIONS)
    # ========================================================

    else:

        # ----------------------------------------------------
        # 7.1 DEFINE THE COMPOSABLE CAMERA NODE
        # ----------------------------------------------------

        # Create a component description for the Orbbec camera.
        #
        # A composable node is loaded into a component container
        # instead of being started as a separate executable.
        compose_node = ComposableNode(

            # Package containing the camera driver.
            package="orbbec_camera",

            # C++ plugin implemented by the Orbbec camera driver.
            #
            # This identifies the component that ROS 2 should load.
            plugin="orbbec_camera::OBCameraNodeDriver",

            # Use the camera_name launch argument as the node name.
            name=LaunchConfiguration("camera_name"),

            # The original component description has an empty namespace.
            #
            # PushRosNamespace below provides the camera namespace.
            namespace="",

            # Pass all camera parameters to the component.
            parameters=parameters,
        )

        # ----------------------------------------------------
        # 7.2 CREATE THE COMPONENT CONTAINER
        # ----------------------------------------------------

        # Create a container that will run the camera component.
        container = ComposableNodeContainer(

            # Name of the component container.
            name="camera_container",

            # The original container namespace is empty.
            namespace="",

            # ROS 2 package that provides component containers.
            package="rclcpp_components",

            # Executable that runs the component container.
            executable="component_container",

            # Components that should be loaded into this container.
            #
            # Here, only the Orbbec camera component is loaded.
            composable_node_descriptions=[
                compose_node,
            ],

            # The original code leaves terminal output disabled.
            # Uncomment to display container output.
            # output="screen",
        )

        # ----------------------------------------------------
        # 7.3 CREATE THE COMPLETE LAUNCH DESCRIPTION
        # ----------------------------------------------------

        # Create the launch description for ROS 2 distributions
        # other than Foxy.
        ld = LaunchDescription(

            # Register all camera configuration arguments.
            args
            +
            [

                # GroupAction allows us to apply a namespace
                # to the actions inside this group.
                GroupAction(

                    [

                        # Apply the camera_name namespace.
                        #
                        # Default:
                        # /camera
                        PushRosNamespace(
                            LaunchConfiguration("camera_name")
                        ),

                        # Start the component container.
                        #
                        # The Orbbec camera component will run
                        # inside this container.
                        container

                    ]
                )
            ]
        )

        # Return the launch description.
        return ld


# ============================================================
# END OF LAUNCH FILE
# ============================================================
