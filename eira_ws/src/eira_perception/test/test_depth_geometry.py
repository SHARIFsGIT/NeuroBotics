"""Exercise depth units, sampling fallbacks and raster calibration without ROS/GPU.

Author: E-AIRA maintainers.
Hardware target: Dabai DCW2 / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

import math

import numpy as np
import pytest

from eira_perception.depth_geometry import (
    estimate_bbox_depth, normalize_depth, resize_depth, sample_depth, scale_intrinsics,
)


@pytest.mark.parametrize('encoding', ['16UC1', 'mono16'])
def test_millimetre_encodings_are_explicit(encoding: str) -> None:
    """Both supported unsigned 16-bit encodings convert millimetres to metres.

    Args:
        encoding: Declared metric depth encoding.
    """
    image = np.array([[0, 850, 1200]], np.uint16)
    converted = normalize_depth(image, encoding)
    assert converted.dtype == np.float64
    assert converted.tolist() == [[0.0, 0.85, 1.2]]
    assert image.dtype == np.uint16 and image[0, 1] == 850


@pytest.mark.parametrize('dtype,encoding', [(np.float32, '32FC1'), (np.float64, '64FC1')])
def test_float_encodings_preserve_units_and_holes(dtype: type, encoding: str) -> None:
    """Floating-point metric input is not divided by 1000 or filled across holes.

    Args:
        dtype: Decoded depth dtype matching the declared encoding.
        encoding: Floating-point ROS image encoding.
    """
    image = np.array([[0.85, np.nan, 0.0, np.inf]], dtype=dtype)
    converted = normalize_depth(image, encoding)
    assert converted[0, 0] == pytest.approx(0.85)
    assert np.isnan(converted[0, 1]) and converted[0, 2] == 0.0
    assert np.isinf(converted[0, 3])


@pytest.mark.parametrize('encoding', ['8UC1', 'mono8'])
def test_eight_bit_data_requires_a_calibrated_scale(encoding: str) -> None:
    """An arbitrary depth visualization must not silently become metric geometry.

    Args:
        encoding: Eight-bit sensor or visualization encoding.
    """
    image = np.array([[0, 85, 120]], np.uint8)
    with pytest.raises(ValueError, match='no known metric depth scale'):
        normalize_depth(image, encoding)
    assert normalize_depth(image, encoding, uint8_scale_m=0.01).tolist() == [[0.0, 0.85, 1.2]]


@pytest.mark.parametrize('image,encoding', [
    (np.zeros((2, 2), np.uint16), '32FC1'),
    (np.zeros((2, 2), np.float32), '16UC1'),
    (np.zeros((2, 2), np.float32), '64FC1'),
    (np.zeros((2, 2), np.uint8), 'rgb8'),
    (np.zeros((2, 2, 3), np.uint8), '8UC1'),
    (np.zeros((0, 0), np.uint16), '16UC1'),
])
def test_unsupported_units_and_shapes_fail_explicitly(image: np.ndarray, encoding: str) -> None:
    """Encoding/dtype disagreement cannot produce a fabricated metre scale.

    Args:
        image: Decoded pixels with malformed geometry or dtype.
        encoding: Declared encoding being checked.
    """
    with pytest.raises(ValueError):
        normalize_depth(image, encoding)


def test_default_roi_is_twenty_one_square_and_ignores_zero_nan() -> None:
    """Holes at the exact center do not defeat the robust neighborhood median."""
    depth = np.full((100, 100), np.nan)
    depth[40:61, 40:61] = 0.85
    depth[50, 50] = 0.0
    depth[49, 49] = np.nan
    depth[48, 48] = np.inf
    result = sample_depth(depth, (30, 30, 70, 70))
    assert result.distance_m == 0.85 and result.source == 'roi_median'
    assert result.roi_total == 21 * 21
    assert result.roi_valid == 21 * 21 - 3
    assert result.center_m == 0.0


def test_empty_center_roi_uses_entire_box_median() -> None:
    """Valid depth away from the cup center remains available through full-box sampling."""
    depth = np.zeros((100, 100), np.float64)
    depth[20:30, 20:30] = 0.8
    depth[70:80, 70:80] = 1.2
    depth[25, 25] = np.nan
    result = sample_depth(depth, (20, 20, 80, 80))
    assert result.source == 'bbox_median'
    assert result.roi_valid == 0 and result.roi_median_m is None
    assert result.distance_m == pytest.approx(1.2)
    assert result.bbox_valid == 199 and result.bbox_total == 3600
    assert result.bbox_min_m == 0.8 and result.bbox_max_m == 1.2


def test_roi_median_takes_priority_over_background_in_box() -> None:
    """The larger box is a fallback and cannot override a usable center neighborhood."""
    depth = np.full((100, 100), 2.5)
    depth[40:61, 40:61] = 0.85
    result = sample_depth(depth, (10, 10, 90, 90))
    assert result.distance_m == 0.85 and result.source == 'roi_median'


def test_small_object_roi_excludes_surrounding_background() -> None:
    """A small cup cannot inherit the majority background depth of an expanded ROI."""
    depth = np.full((40, 40), 2.5)
    depth[15:25, 15:25] = 0.5
    depth[20, 20] = np.nan
    result = sample_depth(depth, (15, 15, 25, 25))
    assert result.distance_m == 0.5 and result.source == 'roi_median'
    assert result.roi_total == 100 and result.roi_valid == 99


def test_small_object_holes_cannot_be_filled_by_background_outside_box() -> None:
    """Unavailable object depth remains unavailable even with valid surrounding surfaces."""
    depth = np.full((40, 40), 2.5)
    depth[15:25, 15:25] = 0.0
    result = sample_depth(depth, (15, 15, 25, 25))
    assert result.distance_m is None and result.source == 'unavailable'
    assert result.roi_total == 100 and result.roi_valid == result.bbox_valid == 0


@pytest.mark.parametrize('box', [
    (-8, 2, -2, 8), (12, 2, 18, 8), (2, -8, 8, -2), (2, 12, 8, 18),
])
def test_nearby_outside_box_cannot_sample_image_border(box: tuple) -> None:
    """A large ROI cannot reach into the image from a box wholly outside it.

    Args:
        box: Off-image detection close enough for its center ROI to reach the image.
    """
    result = sample_depth(np.ones((10, 10)), box)
    assert result.distance_m is None
    assert result.roi_total == result.bbox_total == 0


def test_unavailable_depth_remains_none_without_implicit_estimate() -> None:
    """Pure sampling never quietly substitutes the physical-height prior."""
    depth = np.full((40, 40), np.nan)
    depth[0, 0] = 0.0
    result = sample_depth(depth, (0, 0, 40, 40))
    assert result.distance_m is None and result.source == 'unavailable'
    assert result.bbox_min_m is None and result.bbox_max_m is None


def test_range_filter_reports_excluded_sensor_values_for_debugging() -> None:
    """Range filtering excludes unsafe samples but diagnostics show why they were excluded."""
    depth = np.full((21, 21), 5.0)
    depth[10, 10] = -1.0
    result = sample_depth(depth, (0, 0, 21, 21), min_depth_m=0.1, max_depth_m=3.0)
    assert result.distance_m is None and result.bbox_valid == 0
    assert result.bbox_min_m == result.bbox_max_m == 5.0


def test_roi_and_box_are_clipped_at_image_boundaries() -> None:
    """An edge detection cannot wrap negative indices onto a distant surface."""
    depth = np.full((8, 9), 0.75)
    result = sample_depth(depth, (-3, -2, 5, 4))
    assert result.distance_m == 0.75
    assert result.roi_total <= depth.size and result.bbox_total == 20


def test_outside_box_has_no_sample_instead_of_border_replication() -> None:
    """A completely outside detection cannot claim the image-edge depth."""
    result = sample_depth(np.ones((10, 10)), (50, 50, 60, 60), roi_half=1)
    assert result.distance_m is None
    assert result.roi_total == result.bbox_total == 0
    assert result.center_m is None


@pytest.mark.parametrize('box,half', [
    ((1, 1, 1, 4), 10), ((3, 3, 1, 5), 10), ((0, 0, np.nan, 5), 10),
    ((0, 0, 2, 2), -1), ((0, 0, 2, 2), True),
])
def test_invalid_sampling_geometry_is_rejected(box: tuple, half: int) -> None:
    """Degenerate geometry is rejected before indexing pixels.

    Args:
        box: Bounding box under validation.
        half: Proposed ROI half-width.
    """
    with pytest.raises(ValueError):
        sample_depth(np.ones((10, 10)), box, roi_half=half)


def test_registered_resize_keeps_holes_and_uses_nearest_neighbors() -> None:
    """Resizing does not average valid metres with zero or NaN depth holes."""
    source = np.array([[0.0, 1.0], [np.nan, 2.0]])
    resized = resize_depth(source, 4, 4)
    np.testing.assert_equal(resized, np.repeat(np.repeat(source, 2, axis=0), 2, axis=1))
    assert resize_depth(source, 2, 2) is source


def test_dcw2_resolution_change_scales_vertical_intrinsics() -> None:
    """640x400 depth calibration changes coherently with a 640x480 sampling grid."""
    k = [500.0, 0.0, 320.0, 0.0, 400.0, 200.0, 0.0, 0.0, 1.0]
    assert scale_intrinsics(k, 640, 400, 640, 480) == (500.0, 480.0, 320.0, 240.0)
    fx, fy, cx, cy = scale_intrinsics(k, 640, 400, 320, 200)
    assert (fx, fy, cx, cy) == (250.0, 200.0, 160.0, 100.0)


@pytest.mark.parametrize('k,width,height', [
    ([0.0] * 9, 640, 400), ([1.0] * 8, 640, 400),
    ([1.0] * 9, 0, 400), ([math.nan] * 9, 640, 400),
])
def test_bad_intrinsics_are_rejected(k: list[float], width: int, height: int) -> None:
    """Calibration must have finite focal lengths and known raster dimensions.

    Args:
        k: Proposed camera matrix.
        width: Source width.
        height: Source height.
    """
    with pytest.raises(ValueError):
        scale_intrinsics(k, width, height, 640, 480)


def test_height_estimate_is_a_separate_pinhole_prior() -> None:
    """The ten-centimetre cup prior yields fy times height divided by pixel height."""
    assert estimate_bbox_depth((100, 100, 150, 200), 500.0) == 0.5
    assert estimate_bbox_depth((100, 100, 150, 200), 500.0, real_height_m=0.2) == 1.0


@pytest.mark.parametrize('box,fy,height', [
    ((0, 0, 10, 0), 500., 0.1), ((0, 1, 10, 0), 500., 0.1),
    ((0, 0, 10, 10), 0., 0.1), ((0, 0, 10, 10), 500., 0.),
    ((0, 0, 10, np.nan), 500., 0.1), ((0, 0, 10, 10), np.inf, 0.1),
])
def test_height_estimate_rejects_invalid_geometry(box: tuple, fy: float, height: float) -> None:
    """A failed height prior remains unavailable rather than producing infinite distance.

    Args:
        box: Proposed image box.
        fy: Proposed vertical focal length.
        height: Proposed physical height.
    """
    assert estimate_bbox_depth(box, fy, height) is None
