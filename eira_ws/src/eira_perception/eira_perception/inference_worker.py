"""One killable spawned inference process for bounded E-AIRA camera work.

Author: E-AIRA contributors.
Hardware target: Jetson Orin NX, CUDA-capable Ultralytics and optional ViT tracker.

ROS remains in the parent process. Native inference cannot be safely canceled in
a Python thread, so the parent terminates and joins this isolated process on a
wall-clock timeout. A fixed retry budget controls replacement model processes.
"""

from concurrent.futures import Future
from importlib import import_module
import logging
from multiprocessing import get_context
from multiprocessing.connection import Connection
import os
from pathlib import Path
import sys
import time
from typing import Any

import cv2
import numpy as np

from eira_perception.perception_core import (
    Detection, TargetTrack, color_fraction, intersection_over_union,
)
from eira_perception.tracking_backends import load_transformer


def load_yolo(model_path: Path, source_dir: str = '') -> tuple[Any, str]:
    """Import the installed or explicitly supplied Yahboom YOLO implementation.

    Args:
        model_path: Existing local detector weights.
        source_dir: Optional directory containing the ``ultralytics`` package.

    Returns:
        The YOLO constructor and the resolved package source path.

    Raises:
        FileNotFoundError: If an explicit source directory has no package.
        ImportError: If the selected backend or one of its dependencies is missing.
    """
    # A live robot must never run an implicit pip install while handling a frame.
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    if source_dir:
        root = Path(source_dir).expanduser().resolve()
        if not (root / 'ultralytics' / '__init__.py').is_file():
            raise FileNotFoundError(f'YOLO source directory has no ultralytics package: {root}')
        sys.path.insert(0, str(root))
    try:
        package = import_module('ultralytics')
    except ModuleNotFoundError as exc:
        if source_dir or exc.name != 'ultralytics':
            raise
        # Exercise 31 imports the source tree beside weights/, rather than pip.
        root = model_path.parent.parent.resolve()
        if not (root / 'ultralytics' / '__init__.py').is_file():
            raise ImportError(
                'Ultralytics is unavailable in this Python environment; source the Yahboom '
                'environment or set yolo_source_dir to its directory containing ultralytics'
            ) from exc
        sys.path.insert(0, str(root))
        package = import_module('ultralytics')
    return package.YOLO, str(getattr(package, '__file__', 'unknown'))


class WorkerState:
    """Contain model, identity and transformer state only inside the GPU process."""

    def __init__(self, parameters: dict[str, Any]) -> None:
        """Initialize models without downloading missing artifacts.

        Args:
            parameters: Serializable model settings.

        Raises:
            FileNotFoundError: If detector weights are missing.
            ImportError: If Ultralytics is unavailable.
            RuntimeError: If detector initialization fails.
        """
        path = Path(parameters['model_path']).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f'YOLO weights missing: {path}')
        constructor, self.model_source = load_yolo(path, parameters.get('yolo_source_dir', ''))
        self.model = constructor(str(path))
        names = self.model.names
        self.supported_classes = sorted({str(name).strip().lower() for name in (
            names.values() if isinstance(names, dict) else names
            if isinstance(names, (list, tuple)) else [])})
        self.use_tracker = True
        self._fallback_tracks: dict[int, Detection] = {}
        self._fallback_seen: dict[int, float] = {}
        self._track_lost_s = float(parameters.get('lost_after_s', 1.5))
        self._next_track_id = 0
        self.transformer: Any = None
        self.warning = ''
        if parameters['tracking_backend'] == 'transformer':
            try:
                self.transformer = load_transformer(parameters['tracker_factory'],
                                                    parameters['transformer_model_path'])
            except (ImportError, AttributeError, OSError, ValueError,
                    RuntimeError, cv2.error) as exc:
                self.warning = f'{exc}; falling back to YOLO'
        self.track = TargetTrack(parameters['track_min_iou'])
        self.generation: int | None = None
        self.ready = False
        self.frames = 0
        self.selected: Detection | None = None
        # Constructor completion does not initialize CUDA kernels or the predictor.
        # Charge that first forward pass to the longer model-load timeout.
        if 'imgsz' in parameters:
            size = int(parameters['imgsz'])
            options = {'conf': float(parameters.get('confidence', 0.4)), 'verbose': False,
                       'imgsz': size}
            if parameters.get('device'):
                options['device'] = parameters['device']
            self.model.predict(np.zeros((size, size, 3), dtype=np.uint8), **options)

    def infer(self, payload: dict[str, Any]) -> list[Detection]:
        """Run detector acquisition and optional verified transformer following.

        Args:
            payload: Image, active request generation, class/color and model options.

        Returns:
            Serializable detections with backend IDs.
        """
        frame = payload['frame']
        if (not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3 or
                frame.dtype != np.uint8 or frame.size == 0):
            raise ValueError('YOLO requires a nonempty uint8 BGR image with three channels')
        if self.generation != payload['generation']:
            self.generation = payload['generation']
            self.track.reset()
            self.ready = False
            self.selected = None
        self.frames += 1
        if self.transformer is not None and self.ready and self.frames % payload[
                'transformer_refresh_frames'] != 0:
            try:
                box = self.transformer.update(frame)
                if box is not None and self.selected is not None:
                    return [Detection(tuple(box), self.selected.label, self.selected.confidence,
                                      self.selected.track_id)]
            except (AttributeError, RuntimeError, ValueError, TypeError, cv2.error) as exc:
                self._disable_transformer(exc)
            self.ready = False
        options = {'conf': payload['confidence'], 'verbose': False, 'imgsz': payload['imgsz']}
        if payload['device']:
            options['device'] = payload['device']
        detections = []
        for result in self._detect(frame, options):
            boxes = result.boxes
            if boxes is None:
                continue
            rects = boxes.xyxy.cpu().numpy()
            labels = boxes.cls.cpu().numpy()
            confidences = boxes.conf.cpu().numpy()
            ids = boxes.id.cpu().numpy() if boxes.id is not None else [-1] * len(rects)
            for box, label, confidence, identity in zip(rects, labels, confidences, ids):
                if (not np.isfinite(box).all() or not np.isfinite(confidence) or
                        not np.isfinite(label) or box[2] <= box[0] or box[3] <= box[1]):
                    continue
                name = str(result.names[int(label)]).lower()
                detections.append(Detection(tuple(float(v) for v in box), name,
                                            float(confidence),
                                            int(identity) if np.isfinite(identity) else -1))
        if not self.use_tracker:
            detections = self._associate_fallback(detections)
        candidates = [d for d in detections if d.label == payload['class'] and color_fraction(
            frame, d.box, payload['color']) >= payload['color_min_fraction']]
        self.selected = self.track.select(candidates)
        if self.transformer is not None and self.selected is not None:
            # Reinitialize on each detector verification with the same physical track.
            try:
                self.transformer.initialize(frame, self.selected.box)
                self.ready = True
            except (AttributeError, RuntimeError, ValueError, TypeError, cv2.error) as exc:
                self._disable_transformer(exc)
        return detections

    def _detect(self, frame: np.ndarray, options: dict[str, Any]) -> Any:
        """Degrade a missing optional tracker dependency to regular detection.

        Args:
            frame: BGR image.
            options: Supported detector arguments, excluding tracker-only settings.

        Returns:
            Ultralytics results for this frame.

        Raises:
            ImportError: If a required detector dependency is unavailable.
            RuntimeError: If model inference fails.
        """
        if self.use_tracker:
            try:
                return self.model.track(frame, persist=True, **options)
            except ImportError as exc:
                if str(exc.name).split('.')[0] not in {'lap', 'lapx', 'filterpy'}:
                    raise
                self.use_tracker = False
                # A failed tracker registration may have installed callbacks already.
                self.model.reset_callbacks()
                from eira_brain.console import format_line
                logging.getLogger(__name__).warning(format_line(
                    'VISION', 'Optional YOLO tracker dependency unavailable; '
                    'using detector with local object association', 'warning'))
        return self.model.predict(frame, **options)

    def _associate_fallback(self, detections: list[Detection]) -> list[Detection]:
        """Preserve identities by class and overlap without optional tracker wheels.

        Args:
            detections: Current detector rectangles without tracking identities.

        Returns:
            Detections with persistent local IDs through short detection gaps.
        """
        now = time.monotonic()
        retained = {identity: previous for identity, previous in self._fallback_tracks.items()
                    if now - self._fallback_seen[identity] <= self._track_lost_s}
        available = dict(retained)
        associated = []
        for detection in detections:
            matches = [(intersection_over_union(detection.box, previous.box), identity)
                       for identity, previous in available.items()
                       if previous.label == detection.label]
            overlap, identity = max(matches, default=(0.0, -1))
            if identity >= 0 and overlap >= self.track.minimum_iou:
                available.pop(identity)
            else:
                identity = self._next_track_id
                self._next_track_id += 1
            associated.append(Detection(detection.box, detection.label,
                                        detection.confidence, identity))
        retained.update({d.track_id: d for d in associated})
        self._fallback_tracks = retained
        self._fallback_seen = {identity: self._fallback_seen[identity] for identity in retained
                               if identity in self._fallback_seen}
        self._fallback_seen.update({d.track_id: now for d in associated})
        return associated

    def _disable_transformer(self, error: BaseException) -> None:
        """Degrade incompatible transformer graphs to the already loaded detector.

        Args:
            error: Optional adapter failure.
        """
        self.transformer = None
        self.ready = False
        from eira_brain.console import format_line, sanitize_text
        logging.getLogger(__name__).warning(format_line(
            'VISION', f'Transformer unavailable; using YOLO: {sanitize_text(error)}', 'warning'))


def worker_loop(connection: Connection) -> None:
    """Execute serialized jobs and return failures as data to the ROS parent.

    Args:
        connection: Private duplex pipe owned by one parent and one worker.
    """
    state: WorkerState | None = None
    try:
        while True:
            operation, payload = connection.recv()
            try:
                if operation == 'load':
                    state = WorkerState(payload)
                    result = {'transformer_available': state.transformer is not None,
                              'warning': state.warning, 'model_source': state.model_source,
                              'supported_classes': state.supported_classes}
                elif operation == 'infer' and state is not None:
                    result = state.infer(payload)
                else:
                    raise ValueError('worker requires model initialization before inference')
                connection.send(('ok', result))
            except (ImportError, AttributeError, OSError, RuntimeError, ValueError, TypeError,
                    IndexError, KeyError, OverflowError, AssertionError, cv2.error) as exc:
                connection.send(('error', f'{type(exc).__name__}: {exc}'))
    except (EOFError, BrokenPipeError, OSError):
        return
    finally:
        connection.close()


class InferenceWorker:
    """Maintain at most one native model process and one outstanding Future."""

    def __init__(self) -> None:
        """Prepare spawn isolation without creating a GPU context in the ROS process."""
        self._context = get_context('spawn')
        self._process: Any = None
        self._connection: Connection | None = None
        self._future: Future | None = None

    def submit(self, operation: str, payload: dict[str, Any]) -> Future:
        """Send one job to the persistent process.

        Args:
            operation: Model load or inference operation.
            payload: Serializable settings and optional image pixels.

        Returns:
            Future completed by poll after the child replies.

        Raises:
            RuntimeError: If another job is still outstanding.
            OSError: If the operating system cannot create a process or pipe.
        """
        if self._future is not None and not self._future.done():
            raise RuntimeError('inference worker already busy')
        if self._process is None or not self._process.is_alive():
            self.close()
            self._connection, child = self._context.Pipe()
            self._process = self._context.Process(target=worker_loop, args=(child,), daemon=True)
            self._process.start()
            child.close()
        self._future = Future()
        try:
            self._connection.send((operation, payload))
        except (BrokenPipeError, EOFError, OSError) as exc:
            self._future.set_exception(RuntimeError(f'inference transport failed: {exc}'))
        return self._future

    def poll(self) -> None:
        """Collect a reply without waiting or detect an unexpectedly terminated child."""
        if self._future is None or self._future.done() or self._process is None:
            return
        try:
            if self._connection is not None and self._connection.poll():
                status, result = self._connection.recv()
                if status == 'ok':
                    self._future.set_result(result)
                else:
                    self._future.set_exception(RuntimeError(result))
            elif not self._process.is_alive():
                self._future.set_exception(RuntimeError('inference worker exited unexpectedly'))
        except (EOFError, BrokenPipeError, OSError) as exc:
            self._future.set_exception(RuntimeError(f'inference worker connection closed: {exc}'))

    def close(self) -> None:
        """Terminate native work with bounded joins and release the process/pipe."""
        if self._process is not None:
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=0.5)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(timeout=0.5)
            if not self._process.is_alive():
                self._process.close()
            self._process = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._future is not None and not self._future.done():
            self._future.set_exception(TimeoutError('inference process terminated'))
        self._future = None
