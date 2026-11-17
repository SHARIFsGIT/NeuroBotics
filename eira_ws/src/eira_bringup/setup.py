"""Install E-AIRA orchestration, safety, launch and configuration resources.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'eira_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            [os.path.join('resource', package_name)]),
        (os.path.join('share', package_name), ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
         glob(os.path.join('launch', '*.launch.py'))),
        (os.path.join('share', package_name, 'config'),
         glob(os.path.join('config', '*.yaml')) + glob(os.path.join('config', '*.rviz'))),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='Shariful',
    maintainer_email='shariful@example.com',
    description='E-AIRA master bringup launch and configuration.',
    license='MIT',
    entry_points={'console_scripts': [
        'edge_monitor = eira_bringup.edge_monitor:main',
        'exercise_skills = eira_bringup.exercise_skills:main',
        'arm_state_relay = eira_bringup.arm_state_relay:main',
        'visualization_markers = eira_bringup.visualization_markers:main',
    ]},
)
