"""Test floor coverage and drop geometry with synthetic metric measurements.

Author: E-AIRA maintainers.
Hardware target: Dabai DCW2 on Jetson Orin NX; hardware-free tests.
"""

import numpy as np
import pytest

from eira_bringup.edge_geometry import floor_observation, transform_points


def observe(z: float, count: int = 50) -> dict:
    """Create a rectangular sample cloud at a fixed ground elevation."""
    points = np.column_stack((np.full(count, 0.4), np.zeros(count), np.full(count, z)))
    return floor_observation(points, 0.0, 0.08, 30, 0.15, 0.15, 0.8, 0.25)


def test_level_floor_clear() -> None:
    """Calibrated floor samples should allow motion."""
    assert observe(0.0)['blocked'] is False


def test_drop_blocks() -> None:
    """A lower surface in the driving corridor should block motion."""
    assert observe(-0.2)['reason'] == 'drop_off'


def test_no_return_blocks() -> None:
    """Missing samples are unknown terrain, never a clear floor."""
    assert observe(0.0, 0)['reason'] == 'insufficient_ground'


def test_invalid_depth_not_clear() -> None:
    """Nonfinite points must not satisfy minimum coverage."""
    assert observe(float('nan'))['blocked'] is True


def test_outside_corridor_not_ground_evidence() -> None:
    """A wall beside the path must not satisfy floor coverage."""
    points = np.tile([0.4, 0.5, 0.0], (50, 1))
    assert floor_observation(points, 0.0, 0.08, 30, 0.15, 0.15, 0.8, 0.25)['blocked']


def test_transform_applies_rotation_and_offset() -> None:
    """A quarter-turn and height offset are applied in base coordinates."""
    output = transform_points(np.array([[1.0, 0.0, 0.0]]), (0.0, 0.0, 0.2),
                              (0.0, 0.0, 2**-0.5, 2**-0.5))
    np.testing.assert_allclose(output, [[0.0, 1.0, 0.2]], atol=1e-10)


def test_invalid_quaternion_rejected() -> None:
    """A missing transform rotation cannot be treated as identity."""
    with pytest.raises(ValueError):
        transform_points(np.array([[1.0, 0.0, 0.0]]), (0, 0, 0), (0, 0, 0, 0))


def test_elevated_objects_cannot_prove_floor_clearance() -> None:
    """An object or wall inside the corridor is not evidence of safe floor."""
    assert observe(0.8)['reason'] == 'insufficient_ground'
    assert observe(0.8)['blocked'] is True


@pytest.mark.parametrize('floor_z', [float('nan'), float('inf')])
def test_nonfinite_floor_calibration_rejected(floor_z: float) -> None:
    """A broken calibration must not silently label unknown terrain clear.

    Args:
        floor_z: Invalid floor elevation.
    """
    with pytest.raises(ValueError):
        floor_observation(np.zeros((50, 3)), floor_z, 0.08, 30, 0.15, 0.15, 0.8, 0.25)
