sh start_agent.sh

ros2 launch M3Pro_demo camera_arm_kin.launch.py

ros2 launch M3Pro_navigation base_bringup.launch.py

ros2 run M3Pro_demo grasp_transport

ros2 run M3Pro_demo apriltag_transport_V2

ros2 launch slam_view slam_view.launch.py

ros2 launch M3Pro_navigation navigation2.launch.py map_dir: = /root/M3Pro_ws/src/yahboom_mapping/maps/yahboom_map.yaml

ros2 run yahboom_nav2_bringup rotation_detect_V2

ros2 run yahboom_nav2_bringup get_nav2_status_V2