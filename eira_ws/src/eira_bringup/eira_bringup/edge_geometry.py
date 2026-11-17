"""Pure RGB-D floor safety geometry adapted from exercise 30.

Author: E-AIRA maintainers.
Hardware target: Dabai DCW2 on ROSMASTER M3 Pro / Jetson Orin NX.
"""

import numpy as np


def floor_observation(points: np.ndarray, floor_z: float, drop_m: float,
                      minimum_points: int, drop_fraction: float,
                      x_min: float, x_max: float, half_width: float) -> dict:
    """Classify ground samples in the commanded travel corridor.

    Args:
        points: Nx3 points in base_link, metres.
        floor_z: Calibrated floor elevation in base_link.
        drop_m: Minimum negative height discontinuity.
        minimum_points: Required count of valid corridor samples.
        drop_fraction: Fraction of samples below the floor triggering a stop.
        x_min: Near corridor boundary.
        x_max: Far corridor boundary.
        half_width: Half of the protected corridor width.
    Returns:
        JSON-compatible safety observation, blocked when coverage is insufficient.
    Raises:
        ValueError: If geometry or thresholds are invalid.
    """
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(
            [floor_z, drop_m, drop_fraction, x_min, x_max, half_width]).all() or drop_m <= 0:
        raise ValueError('expected Nx3 points and a positive drop threshold')
    if not 0 < drop_fraction <= 1 or minimum_points < 1 or x_max <= x_min or half_width <= 0:
        raise ValueError('invalid coverage thresholds')
    mask = np.isfinite(points).all(axis=1)
    mask &= (points[:, 0] >= x_min) & (points[:, 0] <= x_max)
    mask &= np.abs(points[:, 1]) <= half_width
    corridor = points[mask]
    count = len(corridor)
    fraction = float(np.mean(corridor[:, 2] < floor_z - drop_m)) if count else 0.0
    # Elevated surfaces (walls, furniture) cannot prove that traversable floor exists.
    ground_count = int(np.count_nonzero(np.abs(corridor[:, 2] - floor_z) <= drop_m))
    unknown = count < minimum_points or ground_count < minimum_points
    return {'blocked': bool(unknown or fraction >= drop_fraction),
            'reason': 'drop_off' if fraction >= drop_fraction else (
                'insufficient_ground' if unknown else 'clear'),
            'sample_count': count, 'ground_count': ground_count, 'drop_fraction': fraction}


def transform_points(points: np.ndarray, translation: tuple, quaternion: tuple) -> np.ndarray:
    """Apply a normalized quaternion rigid transform to row-vector points.

    Args:
        points: Nx3 source coordinates.
        translation: Transform translation x/y/z.
        quaternion: Transform quaternion x/y/z/w.
    Returns:
        Transformed Nx3 coordinates.
    Raises:
        ValueError: If the rotation has zero norm or contains nonfinite values.
    """
    q = np.asarray(quaternion, dtype=float)
    norm = np.linalg.norm(q)
    if not np.isfinite(norm) or norm < 1e-12:
        raise ValueError('invalid transform rotation')
    x, y, z, w = q / norm
    rotation = np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w), 2*(x*z + y*w)],
        [2*(x*y + z*w), 1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x*x + y*y)]])
    return points @ rotation.T + np.asarray(translation, dtype=float)
