"""Verify inference-process isolation and bounded native-work shutdown.

Author: E-AIRA contributors. Hardware target: Jetson Orin NX, ROSMASTER M3 Pro.
"""

import time
from unittest.mock import Mock

import pytest

from eira_perception.inference_worker import InferenceWorker


def test_missing_model_error_crosses_process_boundary_without_gpu() -> None:
    """Absent local weights yield a structured failure without downloading artifacts."""
    worker = InferenceWorker()
    try:
        future = worker.submit('load', {'model_path': '/nonexistent/eira_yolo_weights.pt'})
        deadline = time.monotonic() + 10.0
        while not future.done() and time.monotonic() < deadline:
            worker.poll()
            time.sleep(0.01)
        assert future.done(), 'spawned model worker did not respond before deadline'
        with pytest.raises(RuntimeError, match='weights missing'):
            future.result()
    finally:
        worker.close()
    assert worker._process is None


def test_hung_native_worker_receives_terminate_then_kill() -> None:
    """A native hang cannot leave shutdown waiting on a Python executor thread."""
    worker = InferenceWorker()
    process = Mock()
    process.is_alive.side_effect = [True, True, False]
    worker._process = process
    worker.close()
    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert process.join.call_count == 2
    assert all(call.kwargs['timeout'] <= 0.5 for call in process.join.call_args_list)
    assert worker._process is None
