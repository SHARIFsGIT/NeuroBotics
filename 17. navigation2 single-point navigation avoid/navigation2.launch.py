import os  # (System file operations) - Lets Python work with folders and file paths on your computer.

# A ROS 2 tool that finds the installation directory of a package.
from ament_index_python.packages import get_package_share_directory

# The main container that holds all the launch actions ROS 2 should execute.
from launch import LaunchDescription

# Allows us to declare launch arguments that users can configure when starting the program.
from launch.actions import DeclareLaunchArgument

# Allows this launch file to start another launch file inside itself.
from launch.actions import IncludeLaunchDescription

# Tells ROS 2 how to load another launch file written in Python.
from launch.launch_description_sources import PythonLaunchDescriptionSource

# LaunchConfiguration retrieves the value of a launch argument when the launch system runs.
from launch.substitutions import LaunchConfiguration


# ROS 2 calls this function to get the list of actions that should be launched.
def generate_launch_description():

    # Create a launch configuration named "use_sim_time".
    # It determines whether ROS 2 should use a simulation clock instead of the real clock.
    # "false" means use the normal system/real-time clock by default.
    use_sim_time = LaunchConfiguration("use_sim_time", default="false")

    # Create a launch configuration named "map".
    # This specifies the map file that Nav2 will load for robot navigation.
    map_dir = LaunchConfiguration(
        "map",

        # Build the full path to the default map file.
        # get_package_share_directory("M3Pro_navigation") finds the installed package's share directory.
        # "map" identifies the map folder inside that package.
        # "yahboom_map.yaml" is the YAML file containing map metadata, such as the image path and resolution.
        default=os.path.join(
            get_package_share_directory("M3Pro_navigation"), "map", "yahboom_map.yaml"
        ),
    )

    # Store the name of the navigation parameters file.
    # This file contains settings for Nav2 components, such as planners, controllers, and costmaps.
    param_file_name = "yahboom_M3Pro.yaml"

    # Create a launch configuration named "params_file".
    # It specifies the configuration file that will be passed to Nav2.
    param_dir = LaunchConfiguration(
        "params_file",

        # Build the full path to the parameters file.
        # The file is expected inside the "param" folder of the M3Pro_navigation package.
        default=os.path.join(
            get_package_share_directory("M3Pro_navigation"), "param", param_file_name
        ),
    )

    # Find the directory containing the Nav2 launch files.
    # "nav2_bringup" is a ROS 2 package that provides launch files
    # for starting the Navigation2 system.
    nav2_launch_file_dir = os.path.join(
        get_package_share_directory("nav2_bringup"), "launch"
    )

    # Create and return the complete list of launch actions.
    # ROS 2 uses this LaunchDescription to determine what to start.
    return LaunchDescription(
        [
            # Declare a launch argument named "map".
            # Users can override the default map path when launching this file.
            DeclareLaunchArgument(
                "map",

                # Use the map_dir configuration as the default map path.
                default_value=map_dir,

                # A human-readable description of this argument.
                description="Full path to map file to load",
            ),

            # Declare a launch argument named "params_file".
            # This lets users choose a different Nav2 parameters file if needed.
            DeclareLaunchArgument(
                "params_file",

                # Use param_dir as the default parameters file path.
                default_value=param_dir,

                # Explain what this argument represents.
                description="Full path to param file to load",
            ),

            # Declare a launch argument named "use_sim_time".
            # Set it to "true" when the ROS 2 system should use a simulation clock,
            # for example, when running in Gazebo.
            DeclareLaunchArgument(
                "use_sim_time",

                # The default is "false", so simulation time is disabled.
                default_value="false",

                # Explain the purpose of the argument.
                description="Use simulation (Gazebo) clock if true",
            ),

            # Include and execute the main Nav2 bringup launch file.
            # This starts the navigation system using the selected map and parameters.
            IncludeLaunchDescription(

                # Tell ROS 2 that the launch file being included is written in Python.
                # The path is assembled from the Nav2 launch directory and the file name.
                PythonLaunchDescriptionSource(
                    [nav2_launch_file_dir, "/bringup_launch.py"]
                ),

                # Pass the launch arguments to the included Nav2 launch file.
                # These values configure which map to use, which clock to use,
                # and which parameters file to load.
                launch_arguments={
                    # Tell Nav2 which map to load.
                    "map": map_dir,

                    # Tell Nav2 whether to use simulation time.
                    "use_sim_time": use_sim_time,

                    # Tell Nav2 where to find its parameters file.
                    "params_file": param_dir,

                # Convert the dictionary into key-value pairs that ROS 2 accepts
                # as launch arguments.
                }.items(),
            ),
        ]
    )