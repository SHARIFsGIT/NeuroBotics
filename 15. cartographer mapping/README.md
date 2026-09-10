sh start_agent.sh

ros2 launch slam_mapping bringup.launch.py

ros2 launch slam_mapping cartographer.launch.py

ros2 launch slam_mapping slam_view.launch.py

ros2 run yahboomcar_ctrl yahboom_keyboard

ros2 launch M3Pro_demo camera_arm_kin.launch.py

ros2 run M3Pro_demo follow_line

ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90, joint2: 140, joint3: 20, joint4: 10, joint5: 90, joint6: 180, time: 1500"} --once

ros2 launch slam_mapping save_map.launch.py