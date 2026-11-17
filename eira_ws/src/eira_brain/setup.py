"""Setup.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import os

from setuptools import find_packages, setup

package_name = 'eira_brain'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            [os.path.join('resource', package_name)]),
        (os.path.join('share', package_name), ['package.xml']),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='Shariful',
    maintainer_email='shariful@example.com',
    description=(
        'E-AIRA cognitive layer: LLM task planner that converts natural-language '
        'commands into JSON action sequences and executes them via Nav2.'
    ),
    license='MIT',
    entry_points={
        'console_scripts': [
            'llm_task_planner = eira_brain.llm_task_planner:main',
            'eira_cli = eira_brain.eira_cli:main',
            'waypoint_recorder = eira_brain.waypoint_recorder:main',
            'safety_monitor = eira_brain.safety_monitor:main',
            'velocity_gate = eira_brain.velocity_gate:main',
            'voice_input = eira_brain.voice_activation:main',
            'voice_activation = eira_brain.voice_activation:main',
            'visual_relocalization = eira_brain.visual_relocalization:main',
            'mission_recorder = eira_brain.mission_recorder:main',
            'mission_replayer = eira_brain.mission_replayer:main',
            'mission_reporter = eira_brain.mission_reporter:main',
        ],
    },
)
