from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'eira_manipulation'

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
    zip_safe=True,
    maintainer='Shariful',
    maintainer_email='shariful@example.com',
    description=(
        'E-AIRA manipulation: PID base alignment + IK-driven grasping through '
        'the existing arm_kin service and arm_msgs topics.'
    ),
    license='MIT',
    entry_points={
        'console_scripts': [
            'grasp_executor = eira_manipulation.grasp_executor:main',
        ],
    },
)
