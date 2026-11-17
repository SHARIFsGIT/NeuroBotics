"""Pure RGB-D geometry and target association for E-AIRA.

Author: E-AIRA contributors.
Hardware target: Yahboom ROSMASTER M3 Pro, Jetson Orin NX, Dabai DCW2.
"""

from dataclasses import dataclass
import json
import math
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    """One labeled image-space detection, with optional persistent identity."""

    box: tuple[float, float, float, float]
    label: str
    confidence: float
    track_id: int = -1


def target_request(payload: str) -> dict[str, str]:
    """Decode a correlated request while retaining legacy plain labels.

    Args:
        payload: A label or JSON object with target and correlation fields.

    Returns:
        A normalized request dictionary.

    Raises:
        ValueError: If fields are missing or have invalid types.
    """
    if payload.lstrip().startswith(('{', '[')):
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError('vision request must be an object')
        for key in ('target', 'mission_id', 'action_id'):
            if key in value and not isinstance(value[key], (str, int)):
                raise ValueError(f'{key} must be a string or integer')
        result = {key: str(value.get(key, '')) for key in
                  ('target', 'mission_id', 'action_id')}
    else:
        result = {'target': payload, 'mission_id': '', 'action_id': ''}
    result['target'] = result['target'].strip().lower()
    if not result['target']:
        raise ValueError('target cannot be empty')
    return result


def split_target(request: str) -> tuple[str, str]:
    """Separate an optional color adjective from an exact object class.

    Args:
        request: A class label, optionally prefixed by a supported color.

    Returns:
        The normalized class and optional color name.
    """
    words = request.strip().lower().split()
    colors = {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'white', 'black'}
    if len(words) > 1 and words[0] in colors:
        return ' '.join(words[1:]), words[0]
    return ' '.join(words), ''


def color_fraction(frame: np.ndarray, box: tuple, color: str) -> float:
    """Measure named HSV color coverage inside a clipped detection box.

    Args:
        frame: BGR image.
        box: Bounding box in xyxy pixels.
        color: Supported color name.

    Returns:
        Fraction of pixels matching the requested color, or one without a filter.
    """
    if not color:
        return 1.0
    height, width = frame.shape[:2]
    x0, y0, x1, y1 = (int(v) for v in box)
    roi = frame[max(0, y0):min(height, y1), max(0, x0):min(width, x1)]
    if roi.size == 0:
        return 0.0
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    hue, sat, val = (hsv[:, :, i] for i in range(3))
    ranges = {'blue': (95, 135), 'green': (35, 85), 'yellow': (20, 35),
              'orange': (8, 20), 'purple': (135, 170)}
    if color == 'red':
        mask = ((hue <= 8) | (hue >= 170)) & (sat >= 80) & (val >= 40)
    elif color == 'white':
        mask = (sat <= 45) & (val >= 180)
    elif color == 'black':
        mask = val <= 55
    elif color in ranges:
        lo, hi = ranges[color]
        mask = (hue >= lo) & (hue <= hi) & (sat >= 80) & (val >= 40)
    else:
        return 0.0
    return float(np.count_nonzero(mask) / mask.size)


def intersection_over_union(first: tuple, second: tuple) -> float:
    """Return box overlap normalized by union area.

    Args:
        first: First xyxy rectangle.
        second: Second xyxy rectangle.

    Returns:
        Overlap in the closed interval zero to one.
    """
    width = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    height = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    area1 = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    area2 = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = area1 + area2 - width * height
    return width * height / union if union > 0 else 0.0


class TargetTrack:
    """Keep one object identity until explicitly reset after tracking loss."""

    def __init__(self, minimum_iou: float = 0.3) -> None:
        """Initialize association state.

        Args:
            minimum_iou: Minimum spatial overlap when tracker IDs are absent.
        """
        self.minimum_iou = minimum_iou
        self.track_id: int | None = None
        self.box: tuple | None = None

    def reset(self) -> None:
        """Clear identity and geometry before a new acquisition."""
        self.track_id = None
        self.box = None

    def select(self, candidates: list[Detection]) -> Detection | None:
        """Select the same track, avoiding silent same-class object switches.

        Args:
            candidates: Already class/color-filtered detections.

        Returns:
            The associated detection, or None if the locked object is absent.
        """
        if not candidates:
            return None
        if self.track_id is not None and self.track_id >= 0:
            chosen = next((d for d in candidates if d.track_id == self.track_id), None)
        elif self.box is not None:
            chosen = max(candidates, key=lambda d: intersection_over_union(self.box, d.box))
            if intersection_over_union(self.box, chosen.box) < self.minimum_iou:
                return None
        else:
            chosen = max(candidates, key=lambda d: (d.box[2] - d.box[0]) *
                         (d.box[3] - d.box[1]))
        if chosen is not None:
            self.track_id = chosen.track_id
            self.box = chosen.box
        return chosen


class PositionFilter:
    """Exponential smoothing with reset on excessive time or position changes."""

    def __init__(self, alpha: float = 0.65, reset_gap_s: float = 1.5,
                 maximum_jump_m: float = 0.3) -> None:
        """Configure bounded trajectory smoothing.

        Args:
            alpha: Weight of the newest position, in (0, 1].
            reset_gap_s: Maximum gap before clearing history.
            maximum_jump_m: Displacement that invalidates the old trajectory.

        Raises:
            ValueError: If alpha is outside its supported interval.
        """
        if not 0.0 < alpha <= 1.0:
            raise ValueError('smoothing alpha must be in (0, 1]')
        self.alpha = alpha
        self.reset_gap_s = reset_gap_s
        self.maximum_jump_m = maximum_jump_m
        self.position: np.ndarray | None = None
        self.stamp: float | None = None

    def reset(self) -> None:
        """Clear the accumulated trajectory."""
        self.position = None
        self.stamp = None

    def update(self, position: tuple, stamp: float) -> tuple[float, float, float]:
        """Filter a position in one coordinate frame.

        Args:
            position: Current finite XYZ coordinates in meters.
            stamp: Measurement timestamp in seconds.

        Returns:
            Filtered XYZ coordinates.

        Raises:
            ValueError: If coordinates are nonfinite or timestamps go backward.
        """
        current = np.asarray(position, dtype=float)
        if current.shape != (3,) or not np.isfinite(current).all() or not math.isfinite(stamp):
            raise ValueError('position and timestamp must be finite')
        if self.stamp is not None and stamp <= self.stamp:
            raise ValueError('out-of-order target measurement')
        reset = (self.position is None or self.stamp is None or
                 stamp - self.stamp > self.reset_gap_s or
                 np.linalg.norm(current - self.position) > self.maximum_jump_m)
        self.position = (current if reset else
                         self.alpha * current + (1 - self.alpha) * self.position)
        self.stamp = stamp
        return tuple(float(v) for v in self.position)


def metric_depth(image: np.ndarray) -> np.ndarray:
    """Normalize supported depth encodings without interpreting invalid zeros.

    Args:
        image: uint16 millimeter or floating-point meter depth image.

    Returns:
        A two-dimensional float64 image in meters.

    Raises:
        ValueError: For an unsupported dtype or shape.
    """
    if image.ndim != 2:
        raise ValueError('depth must have exactly two dimensions')
    if image.dtype == np.uint16:
        return image.astype(np.float64) * 0.001
    if image.dtype in (np.float32, np.float64):
        return image.astype(np.float64)
    raise ValueError(f'unsupported depth dtype {image.dtype}')


def object_dimensions(box: tuple, depth_m: float, fx: float, fy: float,
                      thickness_m: float = 0.0, shape: str = 'cuboid') -> dict[str, Any]:
    """Estimate projected dimensions and volume with an explicit thickness prior.

    A single frontal depth image cannot observe the hidden object thickness.
    Volume is therefore None until a calibrated thickness prior is provided;
    projected width and height remain useful measurements for grasp planning.

    Args:
        box: Image-space xyxy bounding box.
        depth_m: Object surface distance.
        fx: Horizontal focal length in pixels.
        fy: Vertical focal length in pixels.
        thickness_m: Calibrated hidden extent; zero disables volume inference.
        shape: Cuboid or cylinder approximation.

    Returns:
        Dimensions, optional estimated volume, method and limitation metadata.

    Raises:
        ValueError: If numeric inputs or requested geometry are invalid.
    """
    if not all(math.isfinite(x) for x in (*box, depth_m, fx, fy, thickness_m)):
        raise ValueError('dimension inputs must be finite')
    if min(depth_m, fx, fy) <= 0 or thickness_m < 0 or shape not in ('cuboid', 'cylinder'):
        raise ValueError('invalid dimension geometry')
    width = max(0.0, box[2] - box[0]) * depth_m / fx
    height = max(0.0, box[3] - box[1]) * depth_m / fy
    volume = None
    if thickness_m > 0:
        volume = (width * height * thickness_m if shape == 'cuboid' else
                  math.pi * width * thickness_m * height / 4.0)
    return {'width_m': width, 'height_m': height, 'thickness_m': thickness_m or None,
            'volume_m3': volume, 'volume_method': f'projected_{shape}_with_thickness_prior',
            'volume_reason': 'thickness_prior_used' if thickness_m > 0 else
                             'hidden_thickness_unobserved',
            'volume_uncertainty': 'bounding geometry estimate; hidden thickness is not measured'}
