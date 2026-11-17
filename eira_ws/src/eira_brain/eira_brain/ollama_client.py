#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ollama_client.py — Local LLM interface for the E-AIRA task planner.

Research role
-------------
This module isolates the *symbolic grounding* step of the pipeline: converting a
free-form natural-language instruction into a machine-checkable JSON action
sequence. It talks to a local Ollama server (default model: Phi-3) so that the
whole system stays fully on-edge, which is one of the paper's claims.

Design notes
------------
* Only the Python standard library is used (urllib) so the node has zero extra
  pip dependencies on the Jetson.
* The prompt fixes a closed action vocabulary that maps 1:1 onto the robot's
  *verified* ROS 2 interfaces discovered in the workspace audit:

      navigate -> nav2_msgs/action/NavigateThroughPoses   (folder 22, V2 script)
      find     -> YOLOv8 acquisition + transformer tracker (folders 31/32/33)
      grasp    -> get_kinemarics IK + arm6_joints          (folder 23)
      release  -> arm_joint / arm6_joints
      home     -> arm6_joints (init pose [90,140,20,10,90,180])
      speak    -> beep topic (UInt16, folder 22 convention)
      stop     -> cancel everything

* `extract_json()` is deliberately defensive: small local models frequently
  wrap JSON in Markdown fences or prepend chatter. The planner falls back to a
  deterministic rule-based parser (in llm_task_planner.py) when the LLM answer
  cannot be parsed — this also gives us the ablation baseline for the paper
  (LLM planner vs. rule-based planner, H1/H2 in the evaluation plan).

Author: E-AIRA contributors.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble.
"""

import json
import re
import time
from typing import Any, Sequence
import urllib.request
import urllib.error

# ============================================================
# PROMPT CONTRACT
# ============================================================

# The closed action vocabulary shared by the LLM, the validator and the
# executor. Keep these three in sync.
KNOWN_ACTIONS = ("navigate", "find", "grasp", "release", "home", "speak", "stop")

# Actions that carry a free-text target argument.
ACTIONS_WITH_TARGET = ("navigate", "find")

COCO_CLASSES = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
    "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
)
TARGET_COLORS = ("red", "blue", "green", "yellow", "orange", "white", "black")
MISSION_START = "mission_start"
PRIMARY_ACTIONS = ("navigate", "find", "grasp", "release", "home", "stop")


def is_stop_command(command: str) -> bool:
    """Recognize imperative stop clauses without confusing the class stop sign.

    Args:
        command: Plain instruction or the standard JSON command envelope.

    Returns:
        Whether any imperative clause asks the robot to stop, halt, cancel, or abort.
    """
    if not isinstance(command, str):
        return False
    text = command.strip()
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, dict) or not isinstance(payload.get("command"), str):
            return False
        text = payload["command"]
    clauses = re.split(r"[.!?;,\n]|\b(?:and(?:\s+then)?|then)\b", text.lower())
    imperative = re.compile(
        r"^(?:(?:please|eira|robot|emergency)\s+)*(?:stop|halt|cancel|abort)\b")
    return any(imperative.match(clause.strip()) is not None for clause in clauses)


def build_system_prompt(waypoints: Sequence[str], object_classes: Sequence[str],
                        colors: Sequence[str] = TARGET_COLORS) -> str:
    """Construct a compact grounded prompt with exactly three valid examples.

    Args:
        waypoints: Named poses available for this planning request.
        object_classes: Detector labels installed on this robot.
        colors: Supported dominant-color filters.

    Returns:
        JSON-only planning instructions and grounded few-shot examples.
    """
    places = sorted({str(name).strip().lower() for name in waypoints if str(name).strip()})
    objects = sorted({str(name).strip().lower() for name in object_classes
                      if str(name).strip()})
    object_name = "cup" if "cup" in objects else (objects[0] if objects else None)
    destination = "kitchen" if "kitchen" in places else next(
        (place for place in places if place != MISSION_START), None)
    examples = []
    if destination:
        examples.append((f"go to the {destination}", [
            {"action": "navigate", "target": destination}]))
    elif object_name:
        examples.append((f"find a {object_name}", [{"action": "find", "target": object_name}]))
    else:
        examples.append(("return the arm home", [{"action": "home"}]))
    if destination and MISSION_START in places and object_name:
        examples.append((f"bring me a {object_name} from the {destination}", [
            {"action": "navigate", "target": destination},
            {"action": "find", "target": object_name},
            {"action": "grasp"},
            {"action": "navigate", "target": MISSION_START},
            {"action": "release"}]))
    elif object_name:
        label = f"red {object_name}" if "red" in colors else object_name
        examples.append((f"pick up the {label}", [
            {"action": "find", "target": label}, {"action": "grasp"}]))
    else:
        examples.append(("open the gripper", [{"action": "release"}]))
    examples.append(("stop", [{"action": "stop"}]))
    lines = [
        "You are a robot task planner. Output ONLY a JSON array.",
        "No markdown, no explanation, no code fences. Start with [ and end with ].",
        "Valid actions: navigate, find, grasp, release, home, stop, speak.",
        'Use {"action":"navigate","target":"waypoint"} or '
        '{"action":"find","target":"object"}.',
        'Use {"action":"grasp"}, {"action":"release"}, {"action":"home"}, '
        '{"action":"stop"}; speak uses {"action":"speak","target":"words to say"}.',
        "Valid targets: any waypoint name or object name from the lists below.",
        "Valid waypoints: " + json.dumps(places),
        "Valid detector classes: " + json.dumps(objects),
        "Supported color prefixes: " + json.dumps(list(colors)),
        "Use only listed waypoints/classes. Preserve requested color prefixes.",
        "Grasp requires a preceding find; navigation, home, and release invalidate it.",
        "Navigate moves the base; home moves only the arm. Release opens the gripper.",
        "Bring/fetch from a place means navigate there first, find exactly the requested "
        "object, grasp, navigate to mission_start, then release. Never substitute another object.",
        "mission_start is the robot pose captured when this mission starts, not the home waypoint. "
        "If mission_start is not listed, fetching is unavailable. Explicit go home uses home.",
        "Sort means find, grasp, navigate to the named bin, release. Do not invent bins.",
        "Return [] if the instruction cannot be represented using these capabilities.",
    ]
    for index, (command, plan) in enumerate(examples, 1):
        lines.extend((f"Example {index} input: " + command,
                      "Output: " + json.dumps(plan, separators=(",", ":"))))
    return "\n".join(lines)


def validate_actions(parsed: Any, waypoints: Sequence[str] | None = None,
                     object_classes: Sequence[str] = COCO_CLASSES,
                     colors: Sequence[str] = TARGET_COLORS,
                     max_steps: int = 64) -> tuple[list[dict[str, str]] | None, str]:
    """Validate all primitive names, targets, and grasp prerequisites atomically.

    Args:
        parsed: Decoded model response or fallback action list.
        waypoints: Allowed navigation names; None supports legacy offline preview.
        object_classes: Explicit detector class vocabulary.
        colors: Supported prefixes for object-class targets.
        max_steps: Maximum accepted plan length.

    Returns:
        Normalized complete plan and a diagnostic; invalid plans return None.
    """
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list) or not parsed or len(parsed) > max_steps:
        return None, "response must contain a nonempty bounded JSON action array"
    places = None if waypoints is None else {name.lower() for name in waypoints}
    classes = {name.lower() for name in object_classes}
    prefixes = {name.lower() for name in colors}
    valid = []
    found = False
    for index, item in enumerate(parsed):
        if not isinstance(item, dict) or set(item) - {"action", "target"}:
            return None, f"step {index}: action must contain only action/target fields"
        if not isinstance(item.get("action"), str):
            return None, f"step {index}: action must be a string"
        action = item["action"].strip().lower()
        target = item.get("target", "")
        if action not in KNOWN_ACTIONS or not isinstance(target, str):
            return None, f"step {index}: unknown action or non-string target"
        target = " ".join(target.strip().lower().split()) if action != "speak" else target.strip()
        if action in ACTIONS_WITH_TARGET and not target:
            return None, f"step {index}: {action} requires a target"
        if action == "navigate" and places is not None and target not in places:
            return None, f"step {index}: unknown waypoint {target!r}"
        if action == "find":
            label = target
            prefix, separator, suffix = target.partition(" ")
            if separator and prefix in prefixes:
                label = suffix
            if label not in classes:
                return None, f"step {index}: unsupported detector class {target!r}"
        if target and action not in (*ACTIONS_WITH_TARGET, "speak"):
            return None, f"step {index}: {action} does not accept a target"
        if action == "grasp" and not found:
            return None, f"step {index}: grasp requires a preceding find"
        if action in ("navigate", "release", "home", "grasp", "stop"):
            found = False
        if action == "find":
            found = True
        entry = {"action": action}
        if target:
            entry["target"] = target
        valid.append(entry)
    return valid, "validated complete action sequence"


SYSTEM_PROMPT = build_system_prompt(("home", "kitchen"), COCO_CLASSES)


class OllamaError(Exception):
    """Raised when the local LLM cannot be reached or answers uselessly."""


class OllamaClient:
    """Bounded local client for Ollama's nonstreaming chat endpoint.

    Args:
        url: Base URL of the local Ollama server.
        model: Installed model tag.
        timeout_s: Timeout for each HTTP attempt.
        retries: Maximum additional attempts before deterministic fallback.
        retry_backoff_s: Base retry delay in seconds.
    """

    def __init__(self, url: str = "http://localhost:11434",
                 model: str = "phi3", timeout_s: float = 30.0,
                 retries: int = 1, retry_backoff_s: float = 0.25,
                 temperature: float = 0.1, max_tokens: int = 256) -> None:
        """Initialize validated dependencies and local state.

        Args:
            url: Local Ollama base URL.
            model: Installed local model tag.
            timeout_s: Per-request timeout in seconds.
            retries: Maximum additional attempts.
            retry_backoff_s: Retry delay in seconds.
            temperature: Sampling temperature for grounded planning.
            max_tokens: Maximum generated tokens per request.
        """
        self.url = url.rstrip("/") + "/api/chat"
        self.model = model
        self.timeout_s = max(0.1, float(timeout_s))
        self.retries = max(0, int(retries))
        self.retry_backoff_s = max(0.0, float(retry_backoff_s))
        self.temperature = max(0.0, min(2.0, float(temperature)))
        self.max_tokens = max(1, int(max_tokens))

    # --------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------

    def generate_plan(self, command: str, *, waypoints: Sequence[str] | None = None,
                      object_classes: Sequence[str] | None = None,
                      colors: Sequence[str] = TARGET_COLORS, repair_reason: str = "") -> str:
        """Send the user command to the LLM and return its raw text answer.

        Args:
            command: Natural-language user instruction.
            waypoints: Snapshot of valid navigation names for this mission.
            object_classes: Snapshot of configured detector labels.
            colors: Supported target color prefixes.
            repair_reason: Validation feedback for one corrected response attempt.

        Returns:
            Nonempty raw model response for cleanup and complete-plan validation.

        Raises:
            OllamaError: Transport, timeout, JSON, or response-schema failure.
        """
        prompt = build_system_prompt(
            ("home", "kitchen") if waypoints is None else waypoints,
            COCO_CLASSES if object_classes is None else object_classes, colors)
        if repair_reason:
            prompt += ("\nYour previous response failed validation: " + repair_reason
                       + ". Correct it and return ONLY the JSON action array.")
        payload = {
            "model": self.model,
            "stream": False,
            # Older Ollama JSON mode forces an object root, conflicting with our
            # action-array contract. Keep array generation prompt-driven and
            # validate the complete parsed plan locally on every response.
            # https://github.com/ollama/ollama/blob/v0.3.14/llm/server.go: jsonGrammar.
            "options": {
                # Low temperature: planning is grounded retrieval, not prose.
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": command},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        try:
            request = urllib.request.Request(
                self.url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        except (ValueError, TypeError) as exc:
            raise OllamaError(f"invalid Ollama request configuration: {exc}") from exc
        body = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                break
            except (urllib.error.URLError, OSError, ValueError) as exc:
                if attempt >= self.retries:
                    raise OllamaError(f"Ollama unavailable: {exc}") from exc
                time.sleep(self.retry_backoff_s * (attempt + 1))

        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise OllamaError(f"Malformed Ollama response: {body}") from exc

        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama returned an empty message")
        return content.strip()


# ============================================================
# ROBUST JSON EXTRACTION
# ============================================================

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_FENCE_MARKER_RE = re.compile(r"```(?:[A-Za-z][A-Za-z0-9_-]*)?[ \t]*(?:\r?\n)?")


def parse_plan_json(text: str) -> list[Any] | None:
    """Recover a complete action array from model prose and Markdown fences.

    Args:
        text: Raw model response, optionally containing surrounding explanations.

    Returns:
        Decoded array, or None when no complete array parses. Multiple arrays
        are rejected rather than silently choosing one. Action validation is
        still required before executing any parsed plan.
    """
    if not isinstance(text, str):
        return None
    candidate = text.strip()
    # Preserve literal backticks inside an already valid JSON string value.
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        parsed = None
    if isinstance(parsed, list):
        return parsed
    candidate = _FENCE_MARKER_RE.sub("", candidate)
    first, last = candidate.find("["), candidate.rfind("]")
    if first < 0 or last < first:
        return None
    try:
        parsed = json.loads(candidate[first:last + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, list) else None


def extract_json(text: str) -> list[Any] | dict[str, Any] | None:
    """Best-effort extraction of a JSON array/dict from an LLM answer.

    Small local models add prose or wrap the payload in code fences. Array
    cleanup is shared with the live planner. Legacy preview clients may also
    return a single object from the whole text, a fenced block or surrounding
    prose; the caller must still validate every action.

    Args:
        text: Raw response text to normalize.

    Returns:
        Parsed action array/object, or None when nothing parses.
    """
    if not isinstance(text, str):
        return None
    array = parse_plan_json(text)
    if array is not None:
        return array
    candidates = [text]

    fence = _FENCE_RE.search(text)
    if fence:
        candidates.append(fence.group(1).strip())

    # Outermost bracketed region — robust to trailing commentary.
    lo_arr, hi_arr = text.find("["), text.rfind("]")
    if lo_arr != -1 and hi_arr > lo_arr:
        candidates.append(text[lo_arr:hi_arr + 1])
    lo_obj, hi_obj = text.find("{"), text.rfind("}")
    if lo_obj != -1 and hi_obj > lo_obj:
        candidates.append(text[lo_obj:hi_obj + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, (list, dict)):
            return parsed
    return None
