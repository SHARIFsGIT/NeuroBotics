"""Bounded local Whisper microphone/file transcription with process isolation.

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
Whisper loads once per worker; timeouts terminate that worker. Nothing is sent
to a cloud service. The planner consumes /eira/voice String transcripts.
"""

import json
import multiprocessing as mp
from pathlib import Path
from queue import Empty, Full
import time
from typing import Any

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from eira_brain.console import error_hint, format_line, sanitize_text


def _whisper_worker(jobs: Any, results: Any, settings: dict[str, Any]) -> None:
    """Load one local model and transcribe serialized audio jobs.

    Args:
        jobs: Multiprocessing job queue.
        results: Multiprocessing result queue.
        settings: Model, capture, and device settings.
    """
    try:
        import whisper
        import numpy as np
        model_name = settings["model"]
        cache = Path(settings["model_dir"]).expanduser()
        # Require preinstalled local weights; avoid implicit network downloads.
        weight = Path(model_name).expanduser()
        if not weight.is_file():
            weight = cache / f"{model_name}.pt"
        if not weight.is_file():
            raise FileNotFoundError(f"local Whisper weights missing: {weight}")
        model = whisper.load_model(str(weight), device=settings["device"])
        results.put({"event": "ready"})
        while True:
            job = jobs.get()
            if job is None:
                return
            try:
                if job["kind"] == "microphone":
                    import sounddevice as sd
                    sample_rate = settings["sample_rate"]
                    audio = sd.rec(int(settings["record_s"] * sample_rate),
                                   samplerate=sample_rate, channels=1, dtype="float32")
                    sd.wait()
                    audio = np.asarray(audio[:, 0])
                    if sample_rate != 16000:
                        raise ValueError("Whisper microphone input requires 16000 Hz")
                    if float(np.sqrt(np.mean(audio ** 2))) < settings["min_rms"]:
                        results.put({"event": "silence"})
                        continue
                else:
                    audio = job["path"]
                answer = model.transcribe(audio, language=settings["language"] or None,
                                          fp16=settings["device"] != "cpu")
                text = answer.get("text", "")
                results.put({"event": "transcribed", "text": str(text).strip()})
            except (OSError, RuntimeError, ValueError, ImportError) as exc:
                results.put({"event": "failed", "reason": str(exc)})
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        results.put({"event": "unavailable", "reason": str(exc)})


class VoiceActivation(Node):
    """Manage a bounded local ASR worker and optional wake-word activation.

    Args:
        None.
    """

    def __init__(self) -> None:
        """Declare capture settings without blocking on model loading."""
        super().__init__("voice_activation")
        defaults = {
            "model": "tiny.en", "model_dir": "~/.cache/whisper", "device": "cpu",
            "language": "en", "microphone_enabled": False, "record_s": 4.0,
            "sample_rate": 16000, "min_rms": 0.01, "wake_word": "eira",
            "model_load_timeout_s": 90.0, "transcribe_timeout_s": 30.0,
            "worker_retries": 1, "retry_backoff_s": 5.0,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self._settings = {key: self.get_parameter(key).value for key in defaults}
        self._context = mp.get_context("spawn")
        self._jobs = None
        self._results = None
        self._process = None
        self._ready = False
        self._busy = True
        self._retries = 0
        self._retry_at = None
        self._deadline = None
        self._publisher = self.create_publisher(String, "/eira/voice", 10)
        self._event_pub = self.create_publisher(String, "/eira/voice/event", 10)
        self.create_subscription(String, "/eira/audio_file", self._on_file, 10)
        self.create_timer(0.2, self._poll)
        self._start()

    def _emit(self, event: str, **fields: Any) -> None:
        """Publish structured ASR diagnostics.

        Args:
            event: Lifecycle event name.
            **fields: Event metadata.
        """
        payload = {"event": event, "mission_id": None, "action_id": None,
                   "wall_time": time.time(), **fields}
        text = json.dumps(payload)
        self._event_pub.publish(String(data=text))
        descriptions = {
            'ready': 'Whisper ready for voice input',
            'transcribed': 'Heard: ' + sanitize_text(fields.get('text')),
            'unavailable': 'Voice input unavailable',
            'failed': 'Voice request failed',
        }
        description = descriptions.get(event, sanitize_text(event).replace('_', ' ').capitalize())
        if fields.get('reason'):
            description += ': ' + error_hint(fields['reason'])
        self.get_logger().info(format_line(
            'VOICE', description, 'warning' if event in ('unavailable', 'failed') else 'info'))

    def _start(self) -> None:
        """Start a process with a bounded model initialization period."""
        self._jobs = self._context.Queue(maxsize=1)
        self._results = self._context.Queue(maxsize=4)
        self._process = self._context.Process(
            target=_whisper_worker, args=(self._jobs, self._results, self._settings), daemon=True)
        self._process.start()
        self._ready, self._busy = False, True
        self._deadline = time.monotonic() + float(self._settings["model_load_timeout_s"])

    def _stop_worker(self) -> None:
        """Terminate and reap a stalled ASR process."""
        if self._process is not None:
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(timeout=1.0)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(timeout=1.0)
        self._process = None
        self._jobs.close()
        self._results.close()

    def _fail_worker(self, reason: str) -> None:
        """Schedule a bounded recovery without blocking other ROS nodes.

        Args:
            reason: Worker failure description.
        """
        self._emit("unavailable", reason=reason)
        self._stop_worker()
        self._ready, self._busy = False, False
        self._deadline = None
        if self._retries < int(self._settings["worker_retries"]):
            self._retries += 1
            self._retry_at = time.monotonic() + float(self._settings["retry_backoff_s"])

    def _submit(self, job: dict[str, str]) -> None:
        """Submit one job to a healthy worker.

        Args:
            job: Microphone or local-file transcription request.
        """
        if not self._ready or self._busy:
            return
        try:
            self._jobs.put_nowait(job)
        except Full:
            return
        self._busy = True
        self._deadline = time.monotonic() + float(self._settings["transcribe_timeout_s"])

    def _on_file(self, msg: String) -> None:
        """Transcribe a local audio file through Whisper/ffmpeg.

        Args:
            msg: Existing local audio-file path.
        """
        path = Path(msg.data).expanduser()
        if not path.is_file():
            self._emit("failed", reason="audio file does not exist")
            return
        self._submit({"kind": "file", "path": str(path)})

    def _poll(self) -> None:
        """Process transcripts and restart stalled workers within retry limits."""
        now = time.monotonic()
        if self._retry_at is not None and now >= self._retry_at:
            self._retry_at = None
            self._start()
        if self._process is None:
            return
        try:
            event = self._results.get_nowait()
        except Empty:
            event = None
        if event is not None:
            if event["event"] == "unavailable":
                self._fail_worker(event.get("reason", "ASR initialization failed"))
                return
            self._busy, self._deadline = False, None
            if event["event"] == "ready":
                self._ready = True
            if event["event"] == "transcribed":
                text = event["text"]
                wake = str(self._settings["wake_word"]).strip().lower()
                if not wake or text.lower().startswith(wake):
                    command = text[len(wake):].lstrip(" ,.:;") if wake else text
                    if command:
                        self._publisher.publish(String(data=command))
            self._emit(**event)
        if self._deadline is not None and now >= self._deadline:
            self._fail_worker("ASR worker timeout")
            return
        if self._process is not None and not self._process.is_alive() and event is None:
            self._fail_worker("ASR worker exited")
            return
        if self._ready and not self._busy and self._settings["microphone_enabled"]:
            self._submit({"kind": "microphone"})

    def destroy_node(self) -> None:
        """Reap the ASR worker before ROS shutdown."""
        self._stop_worker()
        super().destroy_node()


def main(args: list[str] | None = None) -> None:
    """Run the optional voice activation node.

    Args:
        args: Optional ROS arguments.
    """
    rclpy.init(args=args)
    node = VoiceActivation()
    try:
        rclpy.spin(node)
    except (ExternalShutdownException, KeyboardInterrupt):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
