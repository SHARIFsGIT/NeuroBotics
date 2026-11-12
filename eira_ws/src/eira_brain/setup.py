from glob import glob
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
        ],
    },
)
