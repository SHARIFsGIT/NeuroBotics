"""Normalize and sample RGB-D measurements with explicit geometry provenance.

Author: E-AIRA maintainers.
Hardware target: Jetson Orin NX / Dabai DCW2, ROS 2 Humble / Python 3.10.
Resizing a registered raster changes sampling dimensions; it does not register
two cameras with different optical frames or infer unknown depth units.
"""

from dataclasses import dataclass
import math
from typing import Sequence

import cv2
import numpy as np


@dataclass(frozen=True)
class DepthSample:
    """Describe the source and diagnostic statistics of one target depth sample.

    Args:
        distance_m: Selected metric median, or None if neither region is valid.
        source: roi_median, bbox_median, or unavailable.
        center_m: Finite original center value, including invalid zero, or None.
        roi_median_m: Median of valid ROI pixels, or None.
        roi_valid: ROI pixels within finite positive configured range.
        roi_total: Number of ROI pixels actually sampled after image clipping.
        bbox_min_m: Minimum finite positive depth in the full box, regardless of range.
        bbox_max_m: Maximum finite positive depth in the full box, regardless of range.
        bbox_valid: Box pixels within the configured valid range.
        bbox_total: Number of box pixels sampled after clipping.
    """

    distance_m: float | None
    source: str
    center_m: float | None
    roi_median_m: float | None
    roi_valid: int
    roi_total: int
    bbox_min_m: float | None
    bbox_max_m: float | None
    bbox_valid: int
    bbox_total: int


def normalize_depth(image: np.ndarray, encoding: str,
                    uint8_scale_m: float = 0.0) -> np.ndarray:
    """Convert explicitly understood scalar encodings into metre-valued float64.

    Args:
        image: Two-dimensional scalar depth raster from passthrough decoding.
        encoding: ROS image encoding, such as 16UC1, mono16, or 32FC1.
        uint8_scale_m: Explicit metres per code for 8-bit data; zero rejects it.

    Returns:
        A new metric image preserving invalid zero, NaN and infinity values.

    Raises:
        ValueError: Geometry, dtype, encoding, or an explicit scale is invalid.
    """
    if not isinstance(image, np.ndarray) or image.ndim != 2 or min(image.shape) <= 0:
        raise ValueError('depth image must be a nonempty scalar two-dimensional array')
    kind = encoding.strip().lower()
    if kind in ('16uc1', 'mono16'):
        if image.dtype.kind != 'u' or image.dtype.itemsize != 2:
            raise ValueError(f'{encoding} requires unsigned 16-bit depth pixels')
        return image.astype(np.float64) / 1000.0
    if kind in ('32fc1', '64fc1'):
        expected_size = 4 if kind == '32fc1' else 8
        if image.dtype.kind != 'f' or image.dtype.itemsize != expected_size:
            raise ValueError(f'{encoding} does not match the decoded floating-point dtype')
        return image.astype(np.float64)
    if kind in ('8uc1', 'mono8'):
        if image.dtype != np.uint8:
            raise ValueError(f'{encoding} requires unsigned 8-bit pixels')
        if not math.isfinite(uint8_scale_m) or uint8_scale_m <= 0:
            raise ValueError(f'{encoding} has no known metric depth scale; '
                             'configure uint8_depth_scale_m only for calibrated raw depth')
        return image.astype(np.float64) * uint8_scale_m
    raise ValueError(f'unsupported depth encoding {encoding!r}; metric units are unknown')


def resize_depth(depth_m: np.ndarray, color_width: int, color_height: int) -> np.ndarray:
    """Resample an already registered depth raster without averaging holes into surfaces.

    Args:
        depth_m: Two-dimensional metric depth raster.
        color_width: Positive output width in pixels.
        color_height: Positive output height in pixels.

    Returns:
        Original raster when dimensions match, otherwise nearest-neighbor resized depth.

    Raises:
        ValueError: Input shape or target dimensions are invalid.
    """
    if depth_m.ndim != 2 or min(depth_m.shape) <= 0 or min(color_width, color_height) <= 0:
        raise ValueError('depth and output image dimensions must be positive')
    if depth_m.shape == (color_height, color_width):
        return depth_m
    return cv2.resize(depth_m, (int(color_width), int(color_height)),
                      interpolation=cv2.INTER_NEAREST)


def scale_intrinsics(k: Sequence[float], source_width: int, source_height: int,
                     target_width: int, target_height: int) -> tuple[float, float, float, float]:
    """Scale a pinhole camera matrix to the actual sampling raster dimensions.

    Args:
        k: Row-major 3x3 camera matrix for the source dimensions.
        source_width: Calibration image width.
        source_height: Calibration image height.
        target_width: Sampling image width.
        target_height: Sampling image height.

    Returns:
        Scaled fx, fy, cx and cy in pixels.

    Raises:
        ValueError: Dimensions or camera matrix entries are invalid.
    """
    if len(k) != 9 or min(source_width, source_height, target_width, target_height) <= 0:
        raise ValueError('camera calibration requires a 3x3 matrix and positive dimensions')
    values = tuple(float(value) for value in k)
    if not all(math.isfinite(value) for value in values) or min(values[0], values[4]) <= 0:
        raise ValueError('camera focal lengths must be positive and intrinsics finite')
    sx, sy = target_width / source_width, target_height / source_height
    return values[0] * sx, values[4] * sy, values[2] * sx, values[5] * sy


def _valid_values(region: np.ndarray, minimum: float, maximum: float) -> np.ndarray:
    """Select finite, positive metric returns inside the configured working range.

    Args:
        region: Depth pixels from one sampling region.
        minimum: Inclusive working-range minimum in metres.
        maximum: Inclusive working-range maximum in metres.

    Returns:
        Flattened valid values; zeros and nonfinite pixels are excluded.
    """
    return region[np.isfinite(region) & (region > 0) & (region >= minimum)
                  & (region <= maximum)]


def sample_depth(depth_m: np.ndarray, box: Sequence[float], roi_half: int = 10,
                 min_depth_m: float = 0.1, max_depth_m: float = 3.0) -> DepthSample:
    """Prefer a robust center ROI median, then fall back to all valid box returns.

    Args:
        depth_m: Metric scalar raster in the same pixel grid as box.
        box: Bounding box xmin, ymin, xmax, ymax, with exclusive upper bounds.
        roi_half: Center-neighborhood half-width; 10 samples up to 21x21 pixels,
            intersected with the detection box to exclude surrounding surfaces.
        min_depth_m: Inclusive minimum usable depth in metres.
        max_depth_m: Inclusive maximum usable depth in metres.

    Returns:
        Selected median and statistics; unavailable depth is explicit None.

    Raises:
        ValueError: Raster, box, ROI size, or depth limits are invalid.
    """
    if depth_m.ndim != 2 or min(depth_m.shape) <= 0:
        raise ValueError('depth raster must be nonempty and two-dimensional')
    if len(box) != 4 or not all(math.isfinite(float(value)) for value in box):
        raise ValueError('bounding box must contain four finite coordinates')
    x0, y0, x1, y1 = (float(value) for value in box)
    if x1 <= x0 or y1 <= y0 or isinstance(roi_half, bool) or not isinstance(
            roi_half, int) or roi_half < 0:
        raise ValueError('bounding box must have area and ROI half-size be nonnegative')
    if not all(math.isfinite(value) for value in (min_depth_m, max_depth_m)) or not (
            0 < min_depth_m <= max_depth_m):
        raise ValueError('depth range must be positive, finite and ordered')
    height, width = depth_m.shape
    u, v = int(round(x0 / 2.0 + x1 / 2.0)), int(round(y0 / 2.0 + y1 / 2.0))
    center = float(depth_m[v, u]) if 0 <= u < width and 0 <= v < height else None
    if center is not None and not math.isfinite(center):
        center = None
    left, right = max(0, min(width, math.floor(x0))), max(0, min(width, math.ceil(x1)))
    top, bottom = max(0, min(height, math.floor(y0))), max(0, min(height, math.ceil(y1)))
    full = depth_m[top:bottom, left:right]
    roi_left, roi_right = max(left, u - roi_half), min(right, u + roi_half + 1)
    roi_top, roi_bottom = max(top, v - roi_half), min(bottom, v + roi_half + 1)
    # Clipping to the object also prevents a nearby, fully off-image box from
    # sampling valid image-border/background pixels through its expanded ROI.
    roi = depth_m[max(top, roi_top):max(top, roi_bottom),
                  max(left, roi_left):max(left, roi_right)]
    valid_roi = _valid_values(roi, min_depth_m, max_depth_m)
    valid_box = _valid_values(full, min_depth_m, max_depth_m)
    positive_box = full[np.isfinite(full) & (full > 0)]
    roi_median = float(np.median(valid_roi)) if valid_roi.size else None
    box_median = float(np.median(valid_box)) if valid_box.size else None
    distance = roi_median if roi_median is not None else box_median
    source = 'roi_median' if roi_median is not None else (
        'bbox_median' if box_median is not None else 'unavailable')
    return DepthSample(distance, source, center, roi_median, int(valid_roi.size), int(roi.size),
                       float(np.min(positive_box)) if positive_box.size else None,
                       float(np.max(positive_box)) if positive_box.size else None,
                       int(valid_box.size), int(full.size))


def estimate_bbox_depth(box: Sequence[float], fy: float,
                        real_height_m: float = 0.1) -> float | None:
    """Estimate axial distance from an assumed object height, separately from depth sampling.

    This pinhole prior is not a measured sensor return and depends on pose,
    occlusion and the object's actual height.

    Args:
        box: Finite xyxy bounding box in the focal length's image grid.
        fy: Positive vertical focal length in pixels.
        real_height_m: Assumed positive physical object height in metres.

    Returns:
        Positive finite height-based estimate, or None for invalid/degenerate inputs.
    """
    if len(box) != 4:
        return None
    try:
        values = [float(value) for value in (*box, fy, real_height_m)]
    except (ValueError, TypeError, OverflowError):
        return None
    if not all(math.isfinite(value) for value in values):
        return None
    pixels = values[3] - values[1]
    if pixels <= 0 or values[4] <= 0 or values[5] <= 0:
        return None
    distance = values[5] * values[4] / pixels
    return float(distance) if math.isfinite(distance) and distance > 0 else None
