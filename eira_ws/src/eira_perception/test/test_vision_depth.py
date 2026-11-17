"""Exercise camera/depth fallback integration without DDS, a GPU, or robot motion.

Author: E-AIRA maintainers.
Hardware target: Dabai DCW2 / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

from copy import deepcopy
import time
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import PointStamped
import numpy as np
import pytest
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image

from eira_perception.depth_geometry import sample_depth
from eira_perception.perception_core import Detection, PositionFilter, TargetTrack
from eira_perception.vision_manager import ImageContext, VisionManager


def image(width: int = 80, height: int = 60, encoding: str = '32FC1',
          stamp: int = 99, frame: str = 'depth_optical') -> Image:
    """Create real ROS metadata while keeping pixel conversion explicitly mocked.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        encoding: Declared scalar/color encoding.
        stamp: Nonzero capture timestamp in ROS seconds.
        frame: Actual optical frame associated with the raster.

    Returns:
        Image message with stable acquisition metadata.
    """
    message = Image()
    message.width, message.height, message.encoding = width, height, encoding
    message.header.stamp.sec, message.header.frame_id = stamp, frame
    return message


def calibration(width: int = 80, height: int = 60, fx: float = 200.0,
                fy: float = 200.0, frame: str = 'depth_optical') -> CameraInfo:
    """Create a calibrated model tied to its declared raster and optical frame.

    Args:
        width: Reference image width.
        height: Reference image height.
        fx: Horizontal focal length in reference pixels.
        fy: Vertical focal length in reference pixels.
        frame: Model's actual optical coordinate frame.

    Returns:
        CameraInfo with a finite nonzero focal model.
    """
    info = CameraInfo()
    info.width, info.height = width, height
    info.header.frame_id = frame
    info.k = [fx, 0.0, width / 2, 0.0, fy, height / 2, 0.0, 0.0, 1.0]
    return info


@pytest.fixture
def vision() -> VisionManager:
    """Build actual callbacks with only camera transport, TF and publications mocked.

    Returns:
        VisionManager with a real filter/association and observable boundaries.
    """
    node = object.__new__(VisionManager)
    parameters = {
        'continuous_mode': True, 'max_fps': 8.0, 'idle_fps': 2.0,
        'depth_registered': True, 'sync_slop_s': 2.0, 'image_freshness_s': 5.0,
        'uint8_depth_scale_m': 0.0, 'camera_info_max_age_s': 60.0,
        'depth_roi_half': 10, 'min_depth_m': 0.1, 'max_depth_m': 3.0,
        'bbox_depth_enabled': True, 'real_object_height_m': 0.1,
        'bbox_depth_class': 'cup',
        'depth_debug': False, 'depth_debug_every_n': 10,
        'camera_optical_frame': 'color_optical', 'target_frame': 'base_link',
        'tf_timeout_s': 0.1, 'color_min_fraction': 0.25,
        'confidence': 0.4, 'imgsz': 416, 'device': '', 'transformer_refresh_frames': 15,
        'volume_thickness_m': 0.0, 'volume_shape': 'cuboid',
    }
    node._parameters = parameters
    node._param = lambda name: parameters[name]
    node._request = {'target': 'cup', 'mission_id': 'depth-test', 'action_id': '0:1'}
    node._generation, node._searching, node._announced = 3, True, False
    node._class, node._color = 'cup', ''
    node._pending, node._pending_context, node._model = None, None, True
    node._last_submit, node._last_camera, node._last_seen = 0.0, None, None
    node._depth_notices, node._depth_debug_frames = {}, 0
    node._camera_info = calibration(frame='color_optical')
    node._depth_camera_info = calibration()
    node._camera_info_received = node._depth_camera_info_received = time.monotonic()
    node._track, node._filter = TargetTrack(), PositionFilter()
    node.get_logger = Mock(return_value=Mock())
    node.get_clock = lambda: SimpleNamespace(now=lambda: Time(seconds=100.0))
    node._bridge, node._submit, node._warn = Mock(), Mock(), Mock()
    node._pose_pub, node._emit, node._annotate = Mock(), Mock(), Mock()
    node._points = []

    def transform(point: PointStamped, frame: str, timeout: object) -> PointStamped:
        """Capture original deprojection and model a deterministic frame boundary.

        Args:
            point: Captured optical point using its real measurement timestamp.
            frame: Required output frame.
            timeout: Existing bounded TF timeout.

        Returns:
            Copied point in the requested frame, without altering capture time.
        """
        node._points.append(deepcopy(point))
        result = deepcopy(point)
        result.header.frame_id = frame
        return result

    node._tf_buffer = SimpleNamespace(transform=transform)
    return node


def context(vision: VisionManager, depth: np.ndarray,
            color_stamp: int = 100, depth_stamp: int = 99) -> ImageContext:
    """Prepare an inference snapshot using real camera metadata.

    Args:
        vision: Test node providing current camera model snapshots.
        depth: Already normalized depth raster in color sampling coordinates.
        color_stamp: RGB acquisition timestamp.
        depth_stamp: Depth acquisition timestamp.

    Returns:
        Captured context independent from subsequent camera calibration callbacks.
    """
    height, width = depth.shape
    return ImageContext(
        vision._generation, np.zeros((height, width, 3), np.uint8), depth,
        image(width, height, 'bgr8', color_stamp, 'color_optical'),
        image(width, height, '32FC1', depth_stamp),
        deepcopy(vision._camera_info), deepcopy(vision._depth_camera_info), (width, height))


def detect(vision: VisionManager, captured: ImageContext) -> dict:
    """Run real depth fusion for a known synthetic cup detection.

    Args:
        vision: Configured test perception callbacks.
        captured: Immutable measurement/model snapshot.

    Returns:
        Found-event fields emitted by the actual integration path.
    """
    vision._process_result([Detection((10.0, 10.0, 50.0, 50.0), 'cup', 0.92, 7)], captured)
    assert vision._emit.call_args.args == ('found',)
    return vision._emit.call_args.kwargs


def test_native_dcw2_dimensions_resize_and_scale_depth_intrinsics(vision: VisionManager) -> None:
    """640x400 depth is sampled on the RGB grid with corresponding scaled calibration."""
    vision._camera_info = calibration(640, 480, 600.0, 600.0, 'color_optical')
    vision._depth_camera_info = calibration(640, 400, 400.0, 300.0)
    vision._bridge.imgmsg_to_cv2.side_effect = [
        np.zeros((480, 640, 3), np.uint8), np.full((400, 640), 1000, np.uint16)]
    vision._on_synced_images(image(640, 480, 'bgr8', 100, 'color_optical'),
                             image(640, 400, '16UC1'))
    captured = vision._pending_context
    assert captured.depth.shape == (480, 640)
    assert captured.original_depth_size == (640, 400)
    assert np.all(captured.depth == 1.0)
    intrinsics, frame, source = vision._depth_model(captured)
    assert intrinsics == pytest.approx((400.0, 360.0, 320.0, 240.0))
    assert frame == 'depth_optical' and source == 'depth'
    vision._submit.assert_called_once()


@pytest.mark.parametrize('encoding,dtype,raw', [
    ('16UC1', np.uint16, 850), ('mono16', np.uint16, 850), ('32FC1', np.float32, 0.85),
])
def test_camera_encoding_controls_metric_units(
        vision: VisionManager, encoding: str, dtype: type, raw: float) -> None:
    """Depth decoding follows explicit units rather than guessing from pixel values.

    Args:
        vision: Perception node with a mocked bridge.
        encoding: Actual supported ROS encoding.
        dtype: Decoded scalar pixel dtype.
        raw: Equivalent physical distance represented by that encoding.
    """
    vision._bridge.imgmsg_to_cv2.return_value = np.full((60, 80), raw, dtype)
    assert np.allclose(vision._decode_depth(image(encoding=encoding)), 0.85)


def test_unknown_8bit_depth_does_not_prevent_detector_submission(vision: VisionManager) -> None:
    """Unsupported metric units remain NaN while RGB acquisition can use the size prior."""
    vision._bridge.imgmsg_to_cv2.side_effect = [
        np.zeros((60, 80, 3), np.uint8), np.full((60, 80), 128, np.uint8)]
    vision._on_synced_images(image(encoding='bgr8', stamp=100, frame='color_optical'),
                             image(encoding='8UC1'))
    assert np.isnan(vision._pending_context.depth).all()
    vision._submit.assert_called_once()
    found = detect(vision, vision._pending_context)
    assert found['depth_source'] == 'bbox_estimate' and found['depth_estimated'] is True
    assert found['depth_m'] == pytest.approx(0.5)
    assert vision._points[0].header.frame_id == 'color_optical'


def test_color_fallback_is_explicit_and_scaled(vision: VisionManager) -> None:
    """A missing depth model uses declared color calibration and reports approximation."""
    vision._depth_camera_info = None
    captured = context(vision, np.ones((60, 80)))
    intrinsics, frame, source = vision._depth_model(captured)
    assert intrinsics == (200.0, 200.0, 40.0, 30.0)
    assert frame == 'color_optical' and source == 'color_approximation'
    assert 'Using color intrinsics for depth (approximation)' in str(
        vision.get_logger().warning.call_args)


def test_wrong_frame_depth_model_is_not_silently_applied(vision: VisionManager) -> None:
    """Calibration from another optical frame cannot override the sampled image model."""
    vision._depth_camera_info.header.frame_id = 'wrong_optical'
    _, frame, source = vision._depth_model(context(vision, np.ones((60, 80))))
    assert frame == 'color_optical' and source == 'color_approximation'


def test_roi_holes_use_full_box_and_keep_depth_acquisition_stamp(vision: VisionManager) -> None:
    """Hole recovery preserves depth provenance and does not substitute processing time."""
    depth = np.ones((60, 80))
    depth[20:41, 20:41] = np.nan
    captured = context(vision, depth)
    found = detect(vision, captured)
    assert found['depth_source'] == 'bbox_median' and found['depth_estimated'] is False
    assert found['measurement_stamp_ns'] == 99_000_000_000
    assert found['color_stamp_ns'] == 100_000_000_000
    assert found['depth_stamp_ns'] == 99_000_000_000
    assert found['pair_skew_s'] == 1.0
    pose = vision._pose_pub.publish.call_args.args[0]
    assert pose.header.stamp.sec == 99 and pose.header.frame_id == 'base_link'
    assert vision._points[0].header.stamp.sec == 99


def test_all_holes_use_color_height_prior_and_color_capture_time(vision: VisionManager) -> None:
    """Size-based range is marked estimated and projected using the RGB ray/model."""
    vision._depth_camera_info.k = [400., 0., 40., 0., 500., 30., 0., 0., 1.]
    found = detect(vision, context(vision, np.zeros((60, 80))))
    assert found['depth_source'] == 'bbox_estimate'
    assert found['depth_estimated'] is True and found['assumed_object_height_m'] == 0.1
    assert found['depth_m'] == pytest.approx(0.5)
    assert found['intrinsics_source'] == 'color_bbox_estimate'
    assert found['measurement_stamp_ns'] == 100_000_000_000
    assert vision._points[0].header.frame_id == 'color_optical'


def test_estimation_switch_off_never_publishes_an_invented_pose(vision: VisionManager) -> None:
    """An operator can require measured depth and decline the object-height fallback."""
    vision._parameters['bbox_depth_enabled'] = False
    captured = context(vision, np.zeros((60, 80)))
    vision._process_result([Detection((10., 10., 50., 50.), 'cup', 0.9, 7)], captured)
    vision._pose_pub.publish.assert_not_called()
    vision._emit.assert_not_called()
    assert any(call.args[0] == 'no_valid_depth' for call in vision._warn.call_args_list)


def test_size_estimate_is_not_applied_to_unknown_classes(vision: VisionManager) -> None:
    """The 10 cm cup assumption cannot silently become a bottle/person size assumption."""
    vision._class = 'bottle'
    assert vision._estimate_bbox_distance((10., 10., 50., 50.),
                                          vision._camera_info, 80, 60) is None


def test_size_estimate_supports_explicitly_calibrated_requested_class(vision: VisionManager) -> None:
    """A bottle prior can be calibrated explicitly without carrying over a cup assumption."""
    vision._class = 'bottle'
    vision._parameters.update({'bbox_depth_class': 'bottle', 'real_object_height_m': 0.24})
    assert vision._estimate_bbox_distance((10., 10., 50., 50.),
                                          vision._camera_info, 80, 60) == pytest.approx(1.2)
    vision._parameters['bbox_depth_class'] = ''
    assert vision._estimate_bbox_distance((10., 10., 50., 50.),
                                          vision._camera_info, 80, 60) is None


@pytest.mark.parametrize('label', ['bottle', 'apple', 'sports ball', 'wine glass'])
def test_measured_depth_localizes_the_requested_object_class(
        vision: VisionManager, label: str) -> None:
    """Calibrated RGB-D fusion accepts any requested model class, ignoring a visible cup."""
    vision._request['target'], vision._class = label, label
    captured = context(vision, np.ones((60, 80)))
    vision._process_result([
        Detection((0., 0., 80., 60.), 'cup', 0.99, 1),
        Detection((10., 10., 50., 50.), label, 0.9, 2)], captured)
    found = vision._emit.call_args.kwargs
    assert found['label'] == label and found['track_id'] == 2
    assert found['depth_estimated'] is False
    vision._pose_pub.publish.assert_called_once()


def test_stale_frames_warn_but_still_reach_detector(vision: VisionManager) -> None:
    """Frames older than the diagnostic window remain processable with honest timestamps."""
    vision._bridge.imgmsg_to_cv2.side_effect = [
        np.zeros((60, 80, 3), np.uint8), np.ones((60, 80), np.float32)]
    color = image(encoding='bgr8', stamp=90, frame='color_optical')
    depth = image(stamp=89)
    vision._on_synced_images(color, depth)
    vision._submit.assert_called_once()
    assert any(call.args[0] == 'image_stale' for call in vision._warn.call_args_list)
    assert vision._pending_context.color_image.header.stamp.sec == 90
    assert vision._pending_context.depth_image.header.stamp.sec == 89


@pytest.mark.parametrize('stamp', [0, 103])
def test_unstamped_or_implausibly_future_frames_remain_invalid(
        vision: VisionManager, stamp: int) -> None:
    """Relaxing old-frame processing does not turn invalid time origins into observations.

    Args:
        vision: Perception callbacks with ROS time fixed at 100 seconds.
        stamp: Zero or beyond the allowed future tolerance.
    """
    with pytest.raises(ValueError, match='timestamp invalid'):
        vision._check_image_time(image(stamp=stamp))


def test_calibration_snapshots_survive_later_callbacks(vision: VisionManager) -> None:
    """A queued image must use its captured models instead of the latest mutable camera info."""
    vision._bridge.imgmsg_to_cv2.side_effect = [
        np.zeros((60, 80, 3), np.uint8), np.ones((60, 80), np.float32)]
    vision._on_synced_images(image(encoding='bgr8', stamp=100, frame='color_optical'), image())
    captured = vision._pending_context
    vision._camera_info.k[0] = 999.0
    vision._depth_camera_info.k[4] = 888.0
    assert captured.color_info.k[0] == 200.0
    assert captured.depth_info.k[4] == 200.0


def test_depth_debug_emits_five_lines_only_on_tenth_target_frame(vision: VisionManager) -> None:
    """The optional debug mode gives useful sampling facts without per-frame spam."""
    captured = context(vision, np.ones((60, 80)))
    box = (10., 10., 50., 50.)
    sample = sample_depth(captured.depth, box)
    intrinsics, _, _ = vision._depth_model(captured)
    vision.get_logger().reset_mock()
    for _ in range(10):
        vision._debug_depth(captured, box, sample, intrinsics)
    vision.get_logger().info.assert_not_called()
    vision._parameters['depth_debug'] = True
    for _ in range(9):
        vision._debug_depth(captured, box, sample, intrinsics)
    vision.get_logger().info.assert_not_called()
    vision._debug_depth(captured, box, sample, intrinsics)
    messages = [call.args[0] for call in vision.get_logger().info.call_args_list]
    assert len(messages) == 5
    assert 'Depth at bbox center:' in messages[0] and '32FC1' in messages[0]
    assert 'Depth ROI median:' in messages[1] and 'valid pixels:' in messages[1]
    assert 'min=' in messages[2] and 'max=' in messages[2]
    assert 'Color image size: 80x60, Depth image size: 80x60' in messages[3]
    assert 'Camera intrinsics: fx=200.000' in messages[4]


def test_rgb_only_stream_still_runs_detector_and_marks_estimated_range(
        vision: VisionManager) -> None:
    """Missing depth must not silence bounding boxes or invent a depth capture stamp."""
    vision._bridge.imgmsg_to_cv2.return_value = np.zeros((60, 80, 3), np.uint8)
    vision._on_color(image(encoding='bgr8', stamp=100, frame='color_optical'))
    captured = vision._pending_context
    vision._submit.assert_called_once()
    assert captured.depth_image is None and np.isnan(captured.depth).all()
    found = detect(vision, captured)
    assert found['depth_estimated'] is True
    assert found['depth_stamp_ns'] is None and found['pair_skew_s'] is None
    assert found['depth_age_s'] is None and not found['depth_resized']
    assert found['measurement_stamp_ns'] == 100_000_000_000


@pytest.mark.parametrize('stamp,matched', [(99, True), (97, False), (0, False), (104, False)])
def test_rgb_selects_only_nearby_stamped_depth(
        vision: VisionManager, stamp: int, matched: bool) -> None:
    """A missing, old, future, or invalid depth sample cannot block RGB inference.

    Args:
        vision: Perception callbacks without transport or GPU work.
        stamp: Latest received depth measurement time.
        matched: Whether the depth capture lies within the configured pair tolerance.
    """
    vision._latest_depth = image(stamp=stamp)
    vision._bridge.imgmsg_to_cv2.side_effect = [
        np.zeros((60, 80, 3), np.uint8), np.ones((60, 80), np.float32)]
    vision._on_color(image(encoding='bgr8', stamp=100, frame='color_optical'))
    captured = vision._pending_context
    assert (captured.depth_image is not None) is matched
    assert vision._bridge.imgmsg_to_cv2.call_count == (2 if matched else 1)
    vision._submit.assert_called_once()


@pytest.mark.parametrize('registered', [True, False])
def test_broken_or_unregistered_depth_does_not_disable_rgb(
        vision: VisionManager, registered: bool) -> None:
    """Color detection continues when depth cannot be decoded or safely registered.

    Args:
        vision: Perception callbacks with conversion mocked at the sensor boundary.
        registered: Whether registration is claimed; valid raster is still required.
    """
    vision._parameters['depth_registered'] = registered
    vision._bridge.imgmsg_to_cv2.side_effect = [
        np.zeros((60, 80, 3), np.uint8), CvBridgeError('invalid depth payload')]
    vision._on_synced_images(image(encoding='bgr8', stamp=100, frame='color_optical'), image())
    vision._submit.assert_called_once()
    assert np.isnan(vision._pending_context.depth).all()
    vision._warn.assert_called_once()
    assert vision._warn.call_args.args[0] == 'depth_unavailable'


def test_missing_calibration_keeps_bounding_boxes_available(vision: VisionManager) -> None:
    """Missing camera models prevent a pose, without making RGB detection fail."""
    captured = context(vision, np.ones((60, 80)))._replace(color_info=None, depth_info=None)
    vision._process_result([Detection((10., 10., 50., 50.), 'cup', 0.9, 7)], captured)
    vision._annotate.assert_called_once()
    vision._pose_pub.publish.assert_not_called()
    assert vision._warn.call_args.args[0] == 'camera_info_missing'


def test_wrong_color_model_never_drives_size_estimation(vision: VisionManager) -> None:
    """Calibration from another RGB optical frame cannot drive a cup-height range."""
    captured = context(vision, np.zeros((60, 80)))
    captured.color_info.header.frame_id = 'unrelated_camera'
    vision._process_result([Detection((10., 10., 50., 50.), 'cup', 0.9, 7)], captured)
    vision._annotate.assert_called_once()
    vision._pose_pub.publish.assert_not_called()


def test_reused_depth_stamp_is_not_republished_as_new_pose(vision: VisionManager) -> None:
    """30 Hz RGB can reuse 10 Hz depth for annotations without fabricating fresh poses."""
    captured = context(vision, np.ones((60, 80)))
    detections = [Detection((10., 10., 50., 50.), 'cup', 0.9, 7)]
    vision._process_result(detections, captured)
    vision._process_result(detections, captured)
    vision._process_result(detections, captured._replace(
        color_image=image(encoding='bgr8', stamp=101, frame='color_optical')))
    assert vision._annotate.call_count == 3
    assert vision._pose_pub.publish.call_count == 1
    assert len(vision._points) == 1


def test_rgb_to_rviz_image_renders_boxes_without_depth_or_tf(vision: VisionManager) -> None:
    """Real cv_bridge/OpenCV rendering survives unavailable depth, camera models and TF."""
    vision._bridge = CvBridge()
    vision._image_pub = Mock()
    vision._image_pub.get_subscription_count.return_value = 1
    vision._annotate = MethodType(VisionManager._annotate, vision)
    vision._camera_info = vision._depth_camera_info = None
    vision._parameters['bbox_depth_enabled'] = False
    source = vision._bridge.cv2_to_imgmsg(np.zeros((60, 80, 3), np.uint8), encoding='bgr8')
    source.header.stamp.sec, source.header.frame_id = 100, 'color_optical'
    vision._on_color(source)
    captured = vision._pending_context
    vision._process_result([Detection((10., 20., 50., 50.), 'cup', 0.9, 7)], captured)
    output = vision._image_pub.publish.call_args.args[0]
    pixels = vision._bridge.imgmsg_to_cv2(output, desired_encoding='bgr8')
    assert output.header == source.header and output.encoding == 'bgr8'
    assert tuple(pixels[30, 10]) == (0, 255, 0)
    assert not np.any(captured.frame), 'annotations must not mutate the inference frame'
    vision._pose_pub.publish.assert_not_called()


def test_rviz_annotation_respects_rgb_channel_order_and_has_no_viewer_cost(
        vision: VisionManager) -> None:
    """Unsubscribed preview does no conversion; subscribed preview keeps BGR colors."""
    vision._image_pub = Mock()
    vision._image_pub.get_subscription_count.return_value = 0
    frame = np.zeros((60, 80, 3), np.uint8)
    frame[:, :, 0] = 255
    source = image(encoding='bgr8', stamp=100, frame='color_optical')
    VisionManager._annotate(vision, frame, [], None, source)
    vision._bridge.cv2_to_imgmsg.assert_not_called()
    vision._bridge = CvBridge()
    vision._image_pub.get_subscription_count.return_value = 1
    VisionManager._annotate(vision, frame, [], None, source)
    output = vision._image_pub.publish.call_args.args[0]
    pixels = vision._bridge.imgmsg_to_cv2(output, desired_encoding='bgr8')
    assert tuple(pixels[30, 10]) == (255, 0, 0)


def test_idle_depth_cache_needs_no_pixel_conversion(vision: VisionManager) -> None:
    """Depth acquisition stays available for the next find while idle work stays cheap."""
    vision._parameters.update({'depth_view_fps': 2.0, 'publish_depth_image': False})
    vision._last_depth_view = 0.0
    vision._distance_pub = Mock()
    vision._distance_pub.get_subscription_count.return_value = 0
    source = image()
    vision._on_depth(source)
    assert vision._latest_depth is source
    vision._bridge.imgmsg_to_cv2.assert_not_called()


@pytest.mark.parametrize('shape', [(0, 0), (0, 80), (60, 0)])
def test_empty_depth_raster_does_not_drop_rgb(
        vision: VisionManager, shape: tuple[int, int]) -> None:
    """Malformed empty scalar depth stays inside the optional geometry failure guard.

    Args:
        vision: Perception callbacks with valid RGB conversion.
        shape: Malformed empty depth raster returned by the sensor decoder.
    """
    vision._bridge.imgmsg_to_cv2.side_effect = [
        np.zeros((60, 80, 3), np.uint8), np.zeros(shape, np.float32)]
    vision._on_synced_images(image(encoding='bgr8', stamp=100, frame='color_optical'), image())
    vision._submit.assert_called_once()
    assert vision._pending_context.depth_image is None
    assert np.isnan(vision._pending_context.depth).all()
