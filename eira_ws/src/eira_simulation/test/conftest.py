"""Expose source packages for simulation tests without building or starting Gazebo.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro simulation / ROS 2 Humble, no hardware activation.
"""

from pathlib import Path
import sys

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[2]
for package in ('eira_simulation', 'eira_perception', 'eira_brain'):
    candidate = str(SOURCE_ROOT / package)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


@pytest.fixture
def native_robot() -> Path:
    """Locate the actual exercise-08 M3 Pro CAD description used by the simulator.

    Returns:
        Existing native URDF path.
    """
    source = SOURCE_ROOT.parent.parent / (
        '08. robot model/neurobotics_ws/src/neurobotics/urdf/neurobotics.urdf')
    assert source.is_file(), 'the supplied exercise-08 M3 Pro model must be present'
    return source
