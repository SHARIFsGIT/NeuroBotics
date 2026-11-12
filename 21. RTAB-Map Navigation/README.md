sh start_agent.sh

cp ~/.ros/rtabmap.db ~

ros2 launch M3Pro_navigation rtab_bringup.launch.py

ros2 topic pub /arm6_joints arm_msgs/msg/ArmJoints {"joint1: 90,joint2: 180,joint3: 5,joint4: 0,joint5: 90,joint6: 0,time: 1500"} --once

ros2 launch rtabmap_launch rtabmap.launch.py rgb_topic:=/camera/color/image_raw depth_topic:=/camera/depth/image_raw camera_info_topic:=/camera/color/camera_info odom_topic:=/odom frame_id:=base_link use_sim_time:=false rviz:=true rtabmap_viz:=false approx_sync:=true approx_sync_max_interval:=0.01 qos:=2 frame_id:=base_link visual_odometry:=false icp_odometry:=false subscribe_scan:=true sync_queue_size:=50 topic_queue_size:=50 database_path:=/home/jetson/rtabmap.db namespace:=/ rviz_cfg:=/home/jetson/yahboomcar_ws/src/slam_view/rviz/slam_rviz.rviz rtabmap_args:="--Mem/IncrementalMemory false"

ros2 launch nav2_bringup navigation_launch.py