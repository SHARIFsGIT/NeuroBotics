sh start_agent.sh

ros2 launch slam_mapping slam_toolbox.launch.py

ros2 launch slam_mapping save_slamtoolbox_map.launch.py

ros2 launch slam_mapping save_slamtoolbox_map.launch.py map_type:=posegraph

$HOME/M3Pro_ws/src/m3pro_bringup/config/common.yaml

ros2 launch m3pro_bringup record_tag.launch.py

$HOME/M3Pro_ws/src/m3pro_bringup/config/aritag_relocation.yaml

ros2 launch M3Pro_navigation toolbox_location_nav.launch.py relocation:=True detection_enabled:=True

ros2 service call /control_detection apriltag_localization/srv/ControlDetection "{command: 0}"

ros2 service call /control_detection apriltag_localization/srv/ControlDetection "{command: 1}"

ros2 service call /control_detection apriltag_localization/srv/ControlDetection "{command: 2}"

$HOME/M3Pro_ws/src/m3pro_bringup/launch/record_tag.launch.py

$HOME/M3Pro_ws/src/M3Pro_navigation/launch/toolbox_location_nav.launch.py