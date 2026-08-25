cmake_minimum_required(VERSION 3.8)
project(neurobotics)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

# Data directories (installed to share/neurobotics/...)
install(DIRECTORY urdf meshes launch config rviz worlds
  DESTINATION share/${PROJECT_NAME}
)

# Python tools (installed to lib/neurobotics/, runnable via 'ros2 run')
install(PROGRAMS
  scripts/teleop.py
  scripts/arm_gui.py
  scripts/line_follow.py
  scripts/obstacle_avoid.py
  scripts/calib_angular.py
  scripts/calib_linear.py
  scripts/lidar_view.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
