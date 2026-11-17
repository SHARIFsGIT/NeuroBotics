"""Exercise ROS callback contracts with mocked camera, TF and topic endpoints.

Author: E-AIRA contributors. Hardware target: Jetson Orin NX, ROSMASTER M3 Pro.
"""

from collections import OrderedDict
from concurrent.futures import Future
import json
import time
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

from geometry_msgs.msg import PointStamped
import numpy as np
import pytest
from sensor_msgs.msg import Image
from std_msgs.msg import String

from eira_perception.perception_core import Detection, PositionFilter, TargetTrack
from eira_perception.vision_manager import ImageContext, VisionManager


def state() -> SimpleNamespace:
    """Create a callback fixture without a ROS domain or GPU.

    Returns:
        Minimal node-like object exposing parameters and mocked publishers.
    """
    parameters = {
        'find_timeout_s': 20.0, 'camera_stale_s': 1.0, 'lost_after_s': 1.5,
        'inference_timeout_s': 0.1, 'model_load_timeout_s': 1.0, 'model_retries': 2,
        'retry_backoff_s': 0.1, 'color_min_fraction': 0.25, 'camera_info_max_age_s': 60.0,
        'depth_roi_half': 1, 'min_depth_m': 0.1, 'max_depth_m': 3.0,
        'camera_optical_frame': 'camera_optical', 'target_frame': 'base_link',
        'tf_timeout_s': 0.1, 'volume_thickness_m': 0.05, 'volume_shape': 'cuboid',
        'continuous_mode': True, 'request_cache_size': 256,
        'max_fps': 8.0, 'idle_fps': 2.0, 'depth_registered': True,
        'confidence': 0.4, 'imgsz': 416, 'device': '', 'transformer_refresh_frames': 15,
        'model_path': '/local/test.pt', 'tracking_backend': 'yolo', 'tracker_factory': '',
        'yolo_source_dir': '', 'color_topic': '/camera/color/image_raw',
        'transformer_model_path': '/local/tracker.onnx', 'track_min_iou': 0.3,
        'image_freshness_s': 5.0, 'bbox_depth_enabled': True, 'real_object_height_m': 0.1,
        'bbox_depth_class': 'cup',
        'uint8_depth_scale_m': 0.0, 'depth_debug': False, 'depth_debug_every_n': 10,
    }
    node = SimpleNamespace(
        _param=lambda name: parameters[name], _request={
            'target': 'cup', 'mission_id': 'm1', 'action_id': 'a1'},
        _class='cup', _color='', _generation=1, _searching=True, _announced=False,
        _deadline=123.0, _last_seen=None, _last_camera=None, _transformer=None,
        _transformer_ready=False, _track=TargetTrack(), _filter=PositionFilter(),
        _log=Mock(), _warn=Mock(), _emit=Mock(), _check_image_time=Mock(), _annotate=Mock(),
        _reload_requested=False, _idle_logged=False, _seen_requests=OrderedDict(),
        _pending=None, _pending_context=None, _model=True, _parameters=parameters,
        _load_attempts=0, _inference_errors=0, _next_load=0.0,
        _camera_info=None, _camera_info_received=None,
        get_logger=Mock(return_value=Mock()),
    )
    node._log_idle = MethodType(VisionManager._log_idle, node)
    node._finish_search = MethodType(VisionManager._finish_search, node)
    node._valid_camera_info = VisionManager._valid_camera_info
    for name in ('_camera_snapshot', '_depth_notice', '_log_depth_format', '_decode_depth',
                 '_depth_model', '_estimate_bbox_distance', '_debug_depth', '_check_target_class'):
        setattr(node, name, MethodType(getattr(VisionManager, name), node))
    return node


def test_keepalive_does_not_extend_search_deadline() -> None:
    """Repeated delivery of a request cannot prevent its timeout indefinitely."""
    node = state()
    VisionManager._on_target(node, String(data=json.dumps(node._request)))
    assert node._deadline == 123.0
    VisionManager._on_target(node, String(data=json.dumps({
        'target': 'red cup', 'mission_id': 'm1', 'action_id': 'a2'})))
    assert node._class == 'cup' and node._color == 'red'
    assert node._generation == 2
    assert node._deadline > time.monotonic()


def test_camera_freeze_emits_correlated_lost() -> None:
    """No camera callbacks after success must still produce tracking loss."""
    node = state()
    node._announced = True
    node._searching = False
    node._last_seen = time.monotonic()
    node._last_camera = time.monotonic() - 3.0
    VisionManager._housekeeping(node)
    node._emit.assert_called_once_with('lost', reason='camera_stale')
    assert not node._announced


def test_old_worker_result_cannot_publish_new_mission_pose() -> None:
    """Discard an inference completed after a different target request arrived."""
    node = state()
    node._pending = Future()
    node._pending.set_result([])
    node._pending_context = (0, None, None, None)
    node._pending_timed_out = False
    node._process_result = Mock()
    VisionManager._poll_worker(node)
    node._process_result.assert_not_called()


def test_worker_failure_is_logged_without_escaping_callback() -> None:
    """A GPU or detector runtime error cannot kill the ROS timer executor."""
    node = state()
    node._pending = Future()
    node._pending.set_exception(RuntimeError('GPU temporarily unavailable'))
    node._pending_context = (1, None, None, None)
    node._pending_timed_out = False
    VisionManager._poll_worker(node)
    node._warn.assert_called_once_with('processing_error', 'GPU temporarily unavailable')


@pytest.mark.parametrize('continuous', [True, False])
def test_tf_uses_image_measurement_time_and_found_correlation(continuous: bool) -> None:
    """Fuse mocked camera/TF topics at measurement time and preserve request IDs."""
    node = state()
    node._parameters['continuous_mode'] = continuous
    node._camera_info = SimpleNamespace(k=[100., 0., 10., 0., 100., 10., 0., 0., 1.],
                                        width=20, height=20,
                                        header=SimpleNamespace(frame_id='camera_optical'))
    node._camera_info_received = time.monotonic()
    node._pose_pub = Mock()
    observed = []

    def transform(point: PointStamped, frame: str, timeout: object) -> PointStamped:
        """Mock the TF service at the original measurement timestamp.

        Args:
            point: Stamped camera point.
            frame: Destination frame.
            timeout: Lookup timeout.

        Returns:
            Transformed point for a known static camera offset.
        """
        observed.append(point.header.stamp.sec)
        result = PointStamped()
        result.header.stamp = point.header.stamp
        result.header.frame_id = frame
        result.point.x, result.point.y, result.point.z = 0.2, 0.0, 0.1
        return result

    node._tf_buffer = SimpleNamespace(transform=transform)
    color = Image()
    color.header.stamp.sec = 123
    color.header.frame_id = 'camera_optical'
    color.width = color.height = 20
    depth = Image()
    depth.header = color.header
    depth.width = depth.height = 20
    depth.encoding = '32FC1'
    detection = Detection((5., 5., 15., 15.), 'cup', 0.9, 7)
    VisionManager._process_result(node, [detection], ImageContext(
        1, np.zeros((20, 20, 3), np.uint8), np.ones((20, 20), np.float32), color, depth,
        node._camera_info, None, (20, 20)))
    assert observed == [123]
    node._pose_pub.publish.assert_called_once()
    found = node._emit.call_args
    assert found.args == ('found',)
    assert found.kwargs['track_id'] == 7
    assert found.kwargs['width_m'] == pytest.approx(0.1)
    assert found.kwargs['volume_m3'] == pytest.approx(0.0005)
    assert not node._searching
    if not continuous:
        assert node._deadline is None
        assert node._generation == 2
        node._log.assert_called_with('idle', detail='idle (no active search)')


def test_event_publisher_attaches_mission_identity() -> None:
    """Wire String events retain their mission/action envelope."""
    node = state()
    node._event_pub = Mock()
    VisionManager._emit(node, 'found', width_m=0.04)
    payload = json.loads(node._event_pub.publish.call_args.args[0].data)
    assert payload['mission_id'] == 'm1'
    assert payload['action_id'] == 'a1'
    assert payload['event'] == 'found'


def test_native_inference_timeout_terminates_worker_and_discards_context() -> None:
    """Wall-clock timeout kills native inference instead of waiting on a thread."""
    node = state()
    node._pending = Future()
    node._pending_context = (1, None, None, None)
    node._pending_started = time.monotonic() - 1.0
    node._pending_timed_out = False
    node._worker = Mock()
    node._model = True
    VisionManager._poll_worker(node)
    node._worker.close.assert_called_once()
    assert node._pending is None
    assert node._pending_context is None
    assert node._model is None
    node._emit.assert_called_once_with('timeout', reason='inference_timeout')


def test_demand_idle_drops_frames_before_conversion_or_inference() -> None:
    """Navigating/idle camera subscriptions must not consume model or image-conversion work."""
    node = state()
    node._parameters['continuous_mode'] = False
    node._searching = False
    node._bridge = Mock()
    node._submit = Mock()
    color, depth = Image(), Image()
    color.width = color.height = depth.width = depth.height = 20
    depth.encoding = '32FC1'
    VisionManager._on_synced_images(node, color, depth)
    VisionManager._on_synced_images(node, Image(), Image())
    node._bridge.imgmsg_to_cv2.assert_not_called()
    node._submit.assert_not_called()
    node._log.assert_called_once_with('idle', detail='idle (no active search)')


@pytest.mark.parametrize('continuous,searching', [(False, True), (True, False)])
def test_frames_are_inferred_only_for_search_or_explicit_continuous_mode(
        continuous: bool, searching: bool) -> None:
    """Demand searches and opt-in continuous operation retain actual RGB-D inference."""
    node = state()
    node._parameters['continuous_mode'] = continuous
    node._searching = searching
    node._last_submit = 0.0
    node._camera_info = None
    node._submit = Mock()
    node._bridge = Mock()
    node._bridge.imgmsg_to_cv2.side_effect = [
        np.zeros((20, 20, 3), np.uint8), np.ones((20, 20), np.float32)]
    color, depth = Image(), Image()
    color.width = color.height = depth.width = depth.height = 20
    depth.encoding = '32FC1'
    VisionManager._on_synced_images(node, color, depth)
    assert node._bridge.imgmsg_to_cv2.call_count == 2
    assert node._submit.call_args.args[0] == 'infer'
    assert node._pending_context[0] == node._generation


def test_demand_timeout_terminates_pending_work_and_prevents_late_pose() -> None:
    """A timed-out search cannot deliver a completed pose or restart from old keepalives."""
    node = state()
    node._parameters['continuous_mode'] = False
    node._deadline = time.monotonic() - 1.0
    node._pending = Future()
    node._pending_context = (node._generation, None, None, None)
    node._worker = Mock()
    old_generation = node._generation
    VisionManager._housekeeping(node)
    node._worker.close.assert_called_once()
    node._emit.assert_called_once_with(
        'timeout', reason='acquisition_timeout',
        detail='No fresh RGB images on /camera/color/image_raw; check the '
               'camera driver, topic name and sensor-data QoS.')
    assert not node._searching and node._deadline is None
    assert node._pending is None and node._model is None
    node._pending = Future()
    node._pending.set_result([])
    node._pending_context = (old_generation, None, None, None)
    node._pending_timed_out = False
    node._process_result = Mock()
    VisionManager._poll_worker(node)
    node._process_result.assert_not_called()


def test_completed_correlated_request_cannot_reopen_from_late_keepalive() -> None:
    """Delivery duplicates after success/timeout must leave demand-mode inference idle."""
    node = state()
    node._parameters['continuous_mode'] = False
    node._searching = False
    request = dict(node._request, action_id='new-find')
    message = String(data=json.dumps(request))
    VisionManager._on_target(node, message)
    assert node._searching
    node._finish_search()
    VisionManager._on_target(node, message)
    assert not node._searching


def test_refresh_is_one_shot_preserves_identity_and_cannot_extend_an_active_deadline() -> None:
    """Explicit arm refreshes obtain new measurements without a continuous detector loop."""
    node = state()
    node._parameters['continuous_mode'] = False
    node._searching = False
    node._track.track_id = 17
    node._track.box = (5.0, 5.0, 15.0, 15.0)
    node._filter.update((0.2, 0.0, 0.1), 1.0)
    request = dict(node._request, action_id='grasp', refresh_id=1)
    VisionManager._on_target(node, String(data=json.dumps(request)))
    assert node._track.track_id == 17 and node._filter.stamp == 1.0
    assert node._request['action_id'] == 'grasp'
    deadline = node._deadline
    VisionManager._on_target(node, String(data=json.dumps(dict(request, refresh_id=2))))
    assert node._deadline == deadline
    node._finish_search()
    VisionManager._on_target(node, String(data=json.dumps(request)))
    assert not node._searching
    VisionManager._on_target(node, String(data=json.dumps(dict(request, refresh_id=2))))
    assert node._searching
    assert node._track.track_id == 17


def test_cancel_matches_mission_and_invalidates_inference_without_publishing_measurement() -> None:
    """Stage cancellation stops only the intended mission and discards its outstanding work."""
    node = state()
    node._parameters['continuous_mode'] = False
    node._pending = Future()
    node._pending_context = (node._generation, None, None, None)
    node._worker = Mock()
    node._pose_pub = Mock()
    wrong = dict(node._request, mission_id='other', cancel=True)
    VisionManager._on_target(node, String(data=json.dumps(wrong)))
    assert node._searching
    node._worker.close.assert_not_called()
    cancel = dict(node._request, action_id='stage-handoff', cancel=True)
    VisionManager._on_target(node, String(data=json.dumps(cancel)))
    assert not node._searching and node._pending is None
    node._worker.close.assert_called_once()
    node._pose_pub.publish.assert_not_called()


@pytest.mark.parametrize('refresh', [True, [], '', '   '])
def test_invalid_refresh_token_is_rejected_without_changing_search(refresh: object) -> None:
    """Malformed optional refresh metadata must not create or reset a search."""
    node = state()
    original = node._deadline
    message = String(data=json.dumps(dict(node._request, refresh_id=refresh)))
    VisionManager._on_target(node, message)
    node._warn.assert_called_once()
    assert node._deadline == original


def test_demand_idle_does_not_report_intentional_pause_as_tracking_loss() -> None:
    """Stopping after acquisition is intentional and must not fabricate an object-loss event."""
    node = state()
    node._parameters['continuous_mode'] = False
    node._searching = False
    node._announced = True
    node._last_seen = time.monotonic() - 10.0
    VisionManager._housekeeping(node)
    node._emit.assert_not_called()


def test_demand_idle_loads_once_but_does_not_restart_failed_work_without_request() -> None:
    """One eager model initialization may warm up; idle retry loops must remain stopped."""
    node = state()
    node._parameters['continuous_mode'] = False
    node._searching = False
    node._model = None
    node._submit = Mock()
    VisionManager._poll_worker(node)
    assert node._submit.call_args.args[0] == 'load'
    node._submit.reset_mock()
    node._load_attempts = 1
    VisionManager._poll_worker(node)
    node._submit.assert_not_called()


def test_model_load_does_not_consume_acquisition_deadline() -> None:
    """Cold initialization has its own bounded timeout before target-search timing begins."""
    node = state()
    node._model = None
    node._searching = False
    VisionManager._on_target(node, String(data=json.dumps(dict(node._request, action_id='new'))))
    assert node._searching and node._deadline is None
    node._pending = Future()
    node._pending.set_result({'transformer_available': False})
    node._pending_context = None
    node._pending_timed_out = False
    VisionManager._poll_worker(node)
    assert node._model is True
    assert node._deadline > time.monotonic()


def test_geometry_failure_never_exhausts_model_retry_budget() -> None:
    """A valid inference with missing calibration must not terminate the detector process."""
    node = state()
    node._process_result = Mock(side_effect=ValueError('missing camera model'))
    for _ in range(5):
        node._pending = Future()
        node._pending.set_result([])
        node._pending_context = (node._generation, None, None, None)
        node._pending_timed_out = False
        VisionManager._poll_worker(node)
    assert node._inference_errors == 0 and node._model is True
    node._emit.assert_not_called()
    assert node._warn.call_args.args[0] == 'geometry_error'


def test_repeated_plain_operator_request_can_start_a_new_search() -> None:
    """A new uncorrelated 'cup' request after success is not mistaken for a DDS duplicate."""
    node = state()
    node._parameters['continuous_mode'] = False
    node._request = {'target': 'cup', 'mission_id': '', 'action_id': ''}
    node._announced, node._searching = True, False
    VisionManager._on_target(node, String(data='cup'))
    assert node._searching and not node._announced
    assert node._deadline > time.monotonic()


@pytest.mark.parametrize('target,label,color', [
    ('bottle', 'bottle', ''), ('red apple', 'apple', 'red'),
    ('wine glass', 'wine glass', ''), ('blue sports ball', 'sports ball', 'blue'),
])
def test_command_selects_requested_class_instead_of_previous_object(
        target: str, label: str, color: str) -> None:
    """Consecutive CLI missions replace the object class and keep their request identity."""
    node = state()
    node._track.select([Detection((0, 0, 10, 10), 'cup', 0.9, 42)])
    request = {'target': target, 'mission_id': 'new-mission', 'action_id': 'find-2'}
    VisionManager._on_target(node, String(data=json.dumps(request)))
    assert (node._class, node._color) == (label, color)
    assert node._request == request
    assert node._track.track_id is None
    assert node._searching


def test_unknown_model_class_fails_with_correlated_actionable_detail() -> None:
    """A model incapable of a request explains that limitation without waiting 20 seconds."""
    node = state()
    node._model_labels = {'cup', 'bottle', 'apple'}
    request = {'target': 'screwdriver', 'mission_id': 'm2', 'action_id': 'find-1'}
    VisionManager._on_target(node, String(data=json.dumps(request)))
    assert node._request == request and not node._searching
    event = node._emit.call_args
    assert event.args == ('failed',)
    assert event.kwargs['reason'] == 'unsupported_target'
    assert 'screwdriver' in event.kwargs['detail']
    assert event.kwargs['supported_classes'] == ['apple', 'bottle', 'cup']


def test_model_load_failure_exposes_original_error_to_cli_event() -> None:
    """Missing model files or dependencies retain useful details across the topic boundary."""
    node = state()
    node._load_attempts = 3
    node._pending = Future()
    node._pending.set_exception(RuntimeError('YOLO weights missing: /models/custom.pt'))
    node._pending_context = None
    node._pending_timed_out = False
    VisionManager._poll_worker(node)
    node._emit.assert_called_once_with(
        'failed', reason='model_unavailable', detail='YOLO weights missing: /models/custom.pt')


def test_depth_or_tf_failure_survives_until_search_timeout_event() -> None:
    """The CLI gets the actual localization blocker even when RGB detection is running."""
    node = state()
    node._warnings = {}
    node._last_camera = time.monotonic()
    node._deadline = time.monotonic() - 1.0
    VisionManager._warn(node, 'tf_error', 'camera_optical has no transform to base_link')
    VisionManager._housekeeping(node)
    node._emit.assert_called_once_with(
        'timeout', reason='acquisition_timeout',
        detail='camera_optical has no transform to base_link')
