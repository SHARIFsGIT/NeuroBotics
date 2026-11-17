"""Validate high-level grasp commands without ROS or device access.

Author: E-AIRA maintainers.
Hardware target: Yahboom ROSMASTER M3 Pro, Jetson Orin NX, six-servo arm.
Angles follow the existing Yahboom degree convention; widths are metres.
"""

import json
import math
from typing import Any


def joint_vector(values: Any, lower: list[float], upper: list[float]) -> list[int]:
    """Validate six finite joint angles against calibrated limits.

    Args:
        values: Six joint angles in degrees.
        lower: Per-joint lower bounds in degrees.
        upper: Per-joint upper bounds in degrees.

    Returns:
        Rounded, validated integer angles.

    Raises:
        ValueError: The vector or limits are malformed or outside limits.
    """
    if not isinstance(values, (list, tuple)) or len(values) != 6:
        raise ValueError('exactly six joint angles are required')
    if len(lower) != 6 or len(upper) != 6:
        raise ValueError('exactly six lower and upper limits are required')
    result = []
    for angle, lo, hi in zip(values, lower, upper):
        angle, lo, hi = float(angle), float(lo), float(hi)
        if not all(math.isfinite(v) for v in (angle, lo, hi)) or lo > hi:
            raise ValueError('joint angles and ordered limits must be finite')
        if not lo <= angle <= hi:
            raise ValueError(f'joint angle {angle} outside [{lo}, {hi}]')
        rounded = int(round(angle))
        if not lo <= rounded <= hi:
            raise ValueError('rounded joint angle exceeds limits')
        result.append(rounded)
    return result


def calibrated_gripper_angle(width_m: float, table_json: str) -> int:
    """Interpolate a measured width/servo-angle calibration without extrapolation.

    Args:
        width_m: Observed grasp width in metres.
        table_json: JSON array of ``[width_m, angle_deg]`` calibration pairs.

    Returns:
        Interpolated gripper angle in degrees.

    Raises:
        ValueError: Calibration is missing, invalid, or does not cover the width.
    """
    try:
        table = json.loads(table_json)
        if not isinstance(table, list) or len(table) < 2:
            raise ValueError('at least two measured calibration points are required')
        points = []
        for pair in table:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError('calibration entries must be [width_m, angle_deg]')
            width, angle = float(pair[0]), float(pair[1])
            if not math.isfinite(width) or width <= 0 or not math.isfinite(angle):
                raise ValueError('calibration must contain finite positive widths')
            if not 0 <= angle <= 180:
                raise ValueError('calibrated gripper angles must lie in [0, 180]')
            points.append((width, angle))
        points.sort()
        if any(a[0] >= b[0] for a, b in zip(points, points[1:])):
            raise ValueError('calibration widths must be distinct')
        if not math.isfinite(width_m) or not points[0][0] <= width_m <= points[-1][0]:
            raise ValueError('object width is outside the measured calibration')
        for (left, a), (right, b) in zip(points, points[1:]):
            if left <= width_m <= right:
                return int(round(a + (b - a) * (width_m - left) / (right - left)))
    except (TypeError, json.JSONDecodeError, OverflowError) as exc:
        raise ValueError('invalid gripper calibration') from exc
    raise ValueError('object width is outside the measured calibration')


def request_envelope(text: str) -> dict[str, Any]:
    """Decode a correlated request while retaining legacy plain commands.

    Args:
        text: String message payload.

    Returns:
        Command, mission/action IDs, and optional sorting target.

    Raises:
        ValueError: JSON structure, IDs, or command are invalid.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {'command': text.strip().lower(), 'mission_id': '', 'action_id': ''}
    if not isinstance(data, dict):
        raise ValueError('manipulation request must be an object or plain command')
    result = {}
    for key in ('command', 'mission_id', 'action_id', 'color'):
        value = data.get(key, '')
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise ValueError(f'{key} must be a string or integer')
        result[key] = str(value).strip()
    target = data.get('target', '')
    if not isinstance(target, (str, dict)):
        raise ValueError('target must be a label or acquisition metadata object')
    result['target'] = target
    result['command'] = result['command'].lower()
    if result['command'] not in ('grasp', 'release', 'home', 'stop'):
        raise ValueError('unsupported manipulation command')
    if bool(result['mission_id']) != bool(result['action_id']):
        raise ValueError('mission_id and action_id must be provided together')
    return result
