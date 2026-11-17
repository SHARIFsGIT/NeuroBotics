"""Exercise the real worker/Ultralytics boundary without CUDA or model downloads.

Author: E-AIRA contributors.
Hardware target: Jetson Orin NX on Yahboom ROSMASTER M3 Pro.
"""

import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from eira_perception import inference_worker
from eira_perception.inference_worker import WorkerState, load_yolo


class Tensor:
    """Provide the tensor conversion API used by Ultralytics result boxes."""

    def __init__(self, values: list) -> None:
        """Store CPU tensor data.

        Args:
            values: Array-like numerical data.
        """
        self.values = np.asarray(values, dtype=float)

    def cpu(self) -> 'Tensor':
        """Return this CPU-backed test tensor.

        Returns:
            The same tensor.
        """
        return self

    def numpy(self) -> np.ndarray:
        """Expose array data.

        Returns:
            Underlying NumPy array.
        """
        return self.values


def result(box: tuple = (10, 10, 30, 30), identity: float | None = 7) -> list:
    """Create one realistic Ultralytics result with optional tracking identity.

    Args:
        box: Bounding rectangle.
        identity: Tracker ID, or None for regular prediction.

    Returns:
        Single-image Ultralytics result list.
    """
    boxes = SimpleNamespace(xyxy=Tensor([box]), cls=Tensor([0]), conf=Tensor([0.9]),
                            id=Tensor([identity]) if identity is not None else None)
    return [SimpleNamespace(boxes=boxes, names={0: 'cup'})]


@pytest.fixture
def model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    """Build a WorkerState with a mocked external YOLO implementation.

    Args:
        tmp_path: Test artifact directory.
        monkeypatch: Scoped patch helper.

    Returns:
        Worker state, mocked model, and model parameters.
    """
    weights = tmp_path / 'yolov8n.pt'
    weights.write_bytes(b'local-test-weights')
    backend = Mock()
    backend.names = {0: 'cup', 1: 'bottle', 2: 'sports ball'}
    backend.track.return_value = result()
    backend.predict.return_value = result(identity=None)
    constructor = Mock(return_value=backend)
    monkeypatch.setattr(inference_worker, 'import_module', lambda name: SimpleNamespace(
        YOLO=constructor, __file__='/vendor/ultralytics/__init__.py'))
    parameters = {'model_path': str(weights), 'tracking_backend': 'yolo',
                  'track_min_iou': 0.3}
    return WorkerState(parameters), backend, parameters


def payload(generation: int = 1) -> dict:
    """Create a normal demand-mode inference request.

    Args:
        generation: Current search generation.

    Returns:
        Serializable worker arguments.
    """
    return {'frame': np.zeros((48, 64, 3), dtype=np.uint8), 'generation': generation,
            'class': 'cup', 'color': '', 'color_min_fraction': 0.25,
            'confidence': 0.4, 'imgsz': 416, 'device': '', 'transformer_refresh_frames': 15}


def test_vendor_source_beside_weights_is_imported_when_not_pip_installed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise 31 source installations work inside a fresh spawned process."""
    root = tmp_path / 'yolov8'
    package = root / 'ultralytics'
    package.mkdir(parents=True)
    (package / '__init__.py').touch()
    calls = []
    constructor = Mock()

    def import_backend(name: str) -> SimpleNamespace:
        """Emulate import resolution before and after adding the vendor path.

        Args:
            name: Requested package name.

        Returns:
            Resolved vendor module.

        Raises:
            ModuleNotFoundError: Before the vendor path is present.
        """
        calls.append(name)
        if str(root) not in sys.path:
            raise ModuleNotFoundError('No module named ultralytics', name='ultralytics')
        return SimpleNamespace(YOLO=constructor, __file__=str(package / '__init__.py'))

    monkeypatch.setattr(inference_worker, 'import_module', import_backend)
    monkeypatch.setattr(sys, 'path', list(sys.path))
    selected, source = load_yolo(root / 'weights' / 'yolov8n.pt')
    assert selected is constructor
    assert source == str(package / '__init__.py')
    assert len(calls) == 2
    assert os.environ['YOLO_AUTOINSTALL'] == 'false'


def test_explicit_vendor_source_is_validated(tmp_path: Path) -> None:
    """An incorrect vendor source path gives an actionable startup error."""
    with pytest.raises(FileNotFoundError, match='no ultralytics package'):
        load_yolo(tmp_path / 'yolov8n.pt', str(tmp_path))


def test_missing_torch_does_not_trigger_unrelated_vendor_import_fallback(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A broken detector dependency remains the original diagnosable error."""
    importer = Mock(side_effect=ModuleNotFoundError('No module named torch', name='torch'))
    monkeypatch.setattr(inference_worker, 'import_module', importer)
    with pytest.raises(ModuleNotFoundError, match='torch'):
        load_yolo(tmp_path / 'weights' / 'yolov8n.pt')
    importer.assert_called_once()


def test_cuda_warmup_runs_during_model_load(model: tuple) -> None:
    """The first CUDA forward is charged to model_load_timeout_s, before real images."""
    _, backend, parameters = model
    WorkerState({**parameters, 'imgsz': 416, 'confidence': 0.35, 'device': '0'})
    frame = backend.predict.call_args.args[0]
    assert frame.shape == (416, 416, 3)
    assert frame.dtype == np.uint8
    assert backend.predict.call_args.kwargs == {
        'imgsz': 416, 'conf': 0.35, 'device': '0', 'verbose': False}
    backend.track.assert_not_called()


def test_model_trained_classes_are_exposed_without_a_fixed_target(model: tuple) -> None:
    """Model metadata, including multiword labels, informs unsupported-request errors."""
    worker, _, _ = model
    assert worker.supported_classes == ['bottle', 'cup', 'sports ball']


def test_native_tracking_preserves_backend_identity_and_bgr_pixels(model: tuple) -> None:
    """Regular operation retains native persist=True tracking and configured options."""
    worker, backend, _ = model
    request = payload()
    request['frame'][:, :, 0] = 255
    detections = worker.infer(request)
    assert detections[0].track_id == 7
    assert backend.track.call_args.args[0] is request['frame']
    assert backend.track.call_args.kwargs == {
        'persist': True, 'conf': 0.4, 'imgsz': 416, 'verbose': False}
    backend.predict.assert_not_called()


def test_missing_optional_tracker_degrades_once_and_preserves_local_ids(model: tuple) -> None:
    """Missing lap does not make detection fail or repeatedly attempt installation."""
    worker, backend, _ = model
    backend.track.side_effect = ModuleNotFoundError('No module named lap', name='lap')
    first = worker.infer(payload())
    backend.predict.return_value = result((11, 10, 31, 30), identity=None)
    second = worker.infer(payload(generation=2))
    assert first[0].track_id == second[0].track_id >= 0
    assert backend.track.call_count == 1
    assert backend.predict.call_count == 2
    backend.reset_callbacks.assert_called_once()
    assert 'persist' not in backend.predict.call_args.kwargs


def test_fallback_does_not_reuse_identity_for_different_object(model: tuple) -> None:
    """An unrelated same-class detection cannot silently inherit a locked target ID."""
    worker, backend, _ = model
    backend.track.side_effect = ModuleNotFoundError('No module named lap', name='lap')
    first = worker.infer(payload())
    backend.predict.return_value = result((40, 30, 60, 45), identity=None)
    second = worker.infer(payload())
    assert first[0].track_id != second[0].track_id
    assert worker.selected is None


def test_fallback_retains_identity_through_transient_empty_frame(
        model: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    """One missed detector frame cannot strand an otherwise valid target lock."""
    worker, backend, _ = model
    clock = Mock(return_value=10.0)
    monkeypatch.setattr(inference_worker.time, 'monotonic', clock)
    backend.track.side_effect = ModuleNotFoundError('No module named lap', name='lap')
    first = worker.infer(payload())
    clock.return_value = 10.5
    backend.predict.return_value = []
    assert worker.infer(payload()) == []
    assert len(worker._fallback_tracks) == 1
    clock.return_value = 11.0
    backend.predict.return_value = result((11, 10, 31, 30), identity=None)
    found = worker.infer(payload(generation=2))
    assert found[0].track_id == first[0].track_id
    assert worker.selected is not None


def test_fallback_retires_identity_after_configured_lost_timeout(
        model: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tracks cannot survive an unbounded gap and acquire unrelated objects later."""
    worker, backend, _ = model
    worker._track_lost_s = 0.75
    clock = Mock(return_value=10.0)
    monkeypatch.setattr(inference_worker.time, 'monotonic', clock)
    backend.track.side_effect = ModuleNotFoundError('No module named lap', name='lap')
    first = worker.infer(payload())
    clock.return_value = 10.76
    backend.predict.return_value = result(identity=None)
    following = worker.infer(payload())
    assert following[0].track_id != first[0].track_id
    assert len(worker._fallback_tracks) == len(worker._fallback_seen) == 1


def test_fallback_prunes_expired_tracks_and_timestamps_even_without_detections(
        model: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated acquisitions retain only entries inside the bounded age window."""
    worker, backend, _ = model
    clock = Mock(return_value=10.0)
    monkeypatch.setattr(inference_worker.time, 'monotonic', clock)
    backend.track.side_effect = ModuleNotFoundError('No module named lap', name='lap')
    for index in range(20):
        clock.return_value = 10.0 + index * 2.0
        worker.infer(payload())
        assert len(worker._fallback_tracks) == len(worker._fallback_seen) == 1
    clock.return_value += 2.0
    backend.predict.return_value = []
    assert worker.infer(payload()) == []
    assert worker._fallback_tracks == worker._fallback_seen == {}


@pytest.mark.parametrize('error', [
    RuntimeError('CUDA out of memory'),
    ModuleNotFoundError('torch missing', name='torch'),
])
def test_model_failures_remain_errors_instead_of_false_tracker_degradation(
        model: tuple, error: Exception) -> None:
    """CUDA and required detector errors retain the bounded parent retry policy."""
    worker, backend, _ = model
    backend.track.side_effect = error
    with pytest.raises(type(error), match=str(error)):
        worker.infer(payload())
    backend.predict.assert_not_called()


def test_nonfinite_tracker_id_is_treated_as_untracked(model: tuple) -> None:
    """A NaN tracker ID cannot crash an otherwise valid detection frame."""
    worker, backend, _ = model
    backend.track.return_value = result(identity=float('nan'))
    assert worker.infer(payload())[0].track_id == -1


@pytest.mark.parametrize('frame', [np.zeros((5, 5), dtype=np.uint8),
                                   np.zeros((5, 5, 3), dtype=np.float32),
                                   np.zeros((0, 5, 3), dtype=np.uint8)])
def test_invalid_camera_arrays_do_not_reach_native_model(model: tuple, frame: np.ndarray) -> None:
    """Input contract errors are rejected before the external CUDA call."""
    worker, backend, _ = model
    request = payload()
    request['frame'] = frame
    with pytest.raises(ValueError, match='uint8 BGR'):
        worker.infer(request)
    backend.track.assert_not_called()
