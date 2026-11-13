#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ollama_client.py — Local LLM interface for the E-AIRA task planner.

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
"""

import json
import re
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

SYSTEM_PROMPT = """\
You are the task planner of a mobile-manipulation household robot.
Convert the user's command into a JSON array of primitive actions.

Allowed actions (JSON objects):
  {"action": "navigate", "target": "<waypoint>"}   drive to a named waypoint
  {"action": "find",     "target": "<object>"}     search for an object with the camera
  {"action": "grasp"}                              grasp the last found object
  {"action": "release"}                            open the gripper and place the object
  {"action": "home"}                               return the arm to its home pose
  {"action": "speak",   "target": "<short phrase>"} acknowledge the user
  {"action": "stop"}                               cancel all motion immediately

Rules:
- Output ONLY the JSON array, no explanations, no Markdown fences.
- Use the order in which the user wants things done.
- If the command mentions a place you do not know, still use the user's word
  as the "target"; the robot validates it against its waypoint database.
- Grasping always requires a preceding "find" of the same object.
- Never invent actions outside the list above.

Examples:
"bring me a cup from the kitchen"
[{"action": "navigate", "target": "kitchen"}, {"action": "find", "target": "cup"}, {"action": "grasp"}, {"action": "navigate", "target": "home"}, {"action": "release"}]

"turn to face me and pick up the bottle"
[{"action": "find", "target": "bottle"}, {"action": "grasp"}]

"stop"
[{"action": "stop"}]
"""


class OllamaError(Exception):
    """Raised when the local LLM cannot be reached or answers uselessly."""


class OllamaClient:
    """Minimal blocking client for the Ollama `/api/chat` HTTP endpoint.

    Parameters
    ----------
    url : str
        Base URL of the Ollama server, e.g. ``http://localhost:11434``.
    model : str
        Model tag served by Ollama, e.g. ``phi3``.
    timeout_s : float
        Per-request timeout. Edge models on the Jetson Orin NX answer in
        1-8 s for prompts of this size; the planner treats timeouts as
        "use the fallback parser" rather than as a hard failure.
    """

    def __init__(self, url: str = "http://localhost:11434",
                 model: str = "phi3", timeout_s: float = 20.0):
        self.url = url.rstrip("/") + "/api/chat"
        self.model = model
        self.timeout_s = timeout_s

    # --------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------

    def generate_plan(self, command: str) -> str:
        """Send the user command to the LLM and return its raw text answer.

        Raises ``OllamaError`` on any transport failure so the caller can
        fall back to the rule-based planner.
        """
        payload = {
            "model": self.model,
            "stream": False,
            "options": {
                # Low temperature: planning is grounded retrieval, not prose.
                "temperature": 0.1,
                "num_predict": 256,
            },
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": command},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise OllamaError(f"Ollama unreachable at {self.url}: {exc}") from exc

        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise OllamaError(f"Malformed Ollama response: {body}") from exc

        if not content or not content.strip():
            raise OllamaError("Ollama returned an empty message")
        return content.strip()


# ============================================================
# ROBUST JSON EXTRACTION
# ============================================================

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str):
    """Best-effort extraction of a JSON array/dict from an LLM answer.

    Small local models add prose ("Sure! Here is the plan:") or wrap the
    payload in code fences. This helper tries, in order:

    1. the whole text,
    2. the first fenced block,
    3. the outermost ``[...]`` substring,
    4. the outermost ``{...}`` substring (single-action answers).

    Returns the parsed object or ``None`` when nothing parses.
    """
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
