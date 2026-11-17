"""Install reproducible E-AIRA simulation resources and adapters.

Author: E-AIRA maintainers.
Hardware target: M3 Pro / ROS 2 Humble Gazebo Classic.
"""

from glob import glob
from pathlib import Path
from setuptools import find_packages, setup

NAME = 'eira_simulation'
setup(
    name=NAME, version='0.1.0', packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + NAME]),
        ('share/' + NAME, ['package.xml', 'README.md']),
        *[('share/' + NAME + '/' + folder,
           [path for path in glob(folder + '/*') if Path(path).is_file()])
          for folder in ('launch', 'config', 'worlds', 'maps', 'behavior_trees')],
    ],
    install_requires=['setuptools'], tests_require=['pytest'], zip_safe=True,
    maintainer='E-AIRA maintainers', maintainer_email='shariful@example.com',
    description='Seeded RGB-D/LiDAR M3 Pro simulation and native-interface adapters.',
    license='MIT',
    entry_points={'console_scripts': [
        'sim_arm_bridge = eira_simulation.sim_arm_bridge:main',
        'sim_depth_noise = eira_simulation.sensor_noise:main',
        'sim_perception_oracle = eira_simulation.perception_oracle:main',
    ]},
)
