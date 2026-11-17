"""Install reproducible E-AIRA mission evaluation and benchmark tools.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

from setuptools import find_packages, setup

setup(
    name='eira_evaluation', version='0.1.0', packages=find_packages(exclude=['test']),
    data_files=[('share/ament_index/resource_index/packages', ['resource/eira_evaluation']),
                ('share/eira_evaluation', ['package.xml', 'README.md'])],
    install_requires=['setuptools'], tests_require=['pytest'], zip_safe=True,
    maintainer='E-AIRA maintainers', maintainer_email='shariful@example.com', license='MIT',
    description='Correlated mission evidence, reproducible metrics and serial benchmark trials.',
    entry_points={'console_scripts': [
        'mission_logger = eira_evaluation.mission_logger:main',
        'metrics_calculator = eira_evaluation.metrics_calculator:main',
        'benchmark = eira_evaluation.benchmark:main',
    ]},
)
