"""Optional transformer tracking adapters for E-AIRA.

Author: E-AIRA contributors.
Hardware target: Jetson Orin NX on Yahboom ROSMASTER M3 Pro.

The exercise-33 folder supplies only a launch file, not the proprietary
smart_tracker model ABI. A deployment can provide a Python factory implementing
initialize(frame, xyxy) and update(frame), or use OpenCV's compatible ViT model.
Unknown ONNX graphs are never assigned invented input/output tensor semantics.
"""

from importlib import import_module
from pathlib import Path
from typing import Any

import cv2
import numpy as np


class OpenCVTransformer:
    """Adapt OpenCV ViT single-object tracking to an xyxy rectangle contract."""

    def __init__(self, model_path: str) -> None:
        """Load a compatible OpenCV ViT ONNX model.

        Args:
            model_path: Path to an OpenCV TrackerVit-compatible ONNX graph.

        Raises:
            RuntimeError: If this OpenCV build has no ViT tracker.
            FileNotFoundError: If weights are absent.
            cv2.error: If weights are incompatible.
        """
        if not Path(model_path).expanduser().is_file():
            raise FileNotFoundError(model_path)
        if not hasattr(cv2, 'TrackerVit_create') or not hasattr(cv2, 'TrackerVit_Params'):
            raise RuntimeError('OpenCV TrackerVit is unavailable; supply a tracker_factory')
        params = cv2.TrackerVit_Params()
        params.net = str(Path(model_path).expanduser())
        self._tracker = cv2.TrackerVit_create(params)

    def initialize(self, frame: np.ndarray, box: tuple) -> None:
        """Acquire the object found by YOLO.

        Args:
            frame: BGR image.
            box: Detection xyxy rectangle.
        """
        x0, y0, x1, y1 = (int(v) for v in box)
        self._tracker.init(frame, (x0, y0, x1 - x0, y1 - y0))

    def update(self, frame: np.ndarray) -> tuple | None:
        """Follow the acquired object.

        Args:
            frame: Current BGR image.

        Returns:
            An xyxy rectangle, or None when tracking fails.
        """
        success, box = self._tracker.update(frame)
        if not success:
            return None
        x, y, width, height = box
        return x, y, x + width, y + height


def load_transformer(factory: str, model_path: str) -> Any:
    """Load a replaceable tracker backend without importing it at startup.

    Args:
        factory: Import path ``module:factory``; empty uses OpenCV ViT.
        model_path: Model path passed to the factory.

    Returns:
        An adapter exposing initialize and update methods.

    Raises:
        ValueError: For malformed plugin names or missing adapter methods.
        ImportError: If the optional adapter dependency is unavailable.
        RuntimeError: If the selected backend cannot initialize.
    """
    if not factory:
        return OpenCVTransformer(model_path)
    module, separator, name = factory.partition(':')
    if not separator or not module or not name:
        raise ValueError('tracker_factory must be module:factory')
    adapter = getattr(import_module(module), name)(model_path)
    if not callable(getattr(adapter, 'initialize', None)) or not callable(
            getattr(adapter, 'update', None)):
        raise ValueError('tracker adapter requires initialize and update methods')
    return adapter
