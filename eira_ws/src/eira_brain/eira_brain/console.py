"""Render robot activity as concise terminal lines without changing ROS payloads.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
This module has no ROS dependencies and never publishes or mutates mission data.
"""

from collections.abc import Mapping, Sequence
import math
import os
import re
import sys
from typing import Any
import unicodedata


_ANSI_ESCAPE = re.compile(
    r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b(?:\[[0-?]*[ -/]*[@-~]|[@-_])')
_LEVEL_COLORS = {'success': '1;32', 'warning': '1;33', 'error': '1;31', 'debug': '2;37'}
_COMPONENT_COLORS = {'BRAIN': '1;36', 'VISION': '1;35', 'ARM': '1;34', 'PLAN': '1;36'}


def sanitize_text(value: object, limit: int = 240) -> str:
    """Make external text safe for one terminal line while preserving readable Unicode.

    Args:
        value: Display value; None becomes an empty string.
        limit: Maximum visible characters; zero or negative preserves the full text.

    Returns:
        Text without escape sequences, controls, bidi overrides, or embedded newlines.
    """
    text = '' if value is None else str(value)
    text = _ANSI_ESCAPE.sub('', text)
    text = ''.join(' ' if unicodedata.category(char) in ('Cc', 'Cf', 'Cs') else char
                   for char in text)
    text = ' '.join(text.split())
    if limit > 0 and len(text) > limit:
        return text[:max(0, limit - 1)] + '…'
    return text


def _use_color(color: bool | None) -> bool:
    """Resolve an explicit preference or common terminal color environment settings.

    Args:
        color: Explicit enabled/disabled value, or None for environment/TTY detection.

    Returns:
        Whether to include ANSI styling in the returned line.
    """
    if color is not None:
        return color
    if 'NO_COLOR' in os.environ:
        return False
    for name in ('FORCE_COLOR', 'RCUTILS_COLORIZED_OUTPUT'):
        if name in os.environ:
            return os.environ[name].strip().lower() not in ('', '0', 'false', 'no')
    if os.environ.get('TERM', '').lower() == 'dumb':
        return False
    return bool(sys.stderr.isatty())


def format_line(component: str, message: str, level: str = 'info', *,
                color: bool | None = None) -> str:
    """Format one clearly labelled activity line, with color restricted to its label.

    Args:
        component: Human-facing source such as BRAIN, VISION, or ARM.
        message: Activity or diagnostic text; newlines/control sequences are removed.
        level: info, success, warning, error, or debug; unknown values use info styling.
        color: Explicit color preference, or None to detect environment/TTY support.

    Returns:
        Safe single-line text with a component label and optional severity label.
    """
    source = sanitize_text(component, 24).upper() or 'E-AIRA'
    normalized_level = level.lower()
    label = f'[{source}]'
    code = _LEVEL_COLORS.get(normalized_level, _COMPONENT_COLORS.get(source, '1;36'))
    if _use_color(color):
        label = f'\033[{code}m{label}\033[0m'
    severity = {'warning': 'WARNING: ', 'error': 'ERROR: ', 'debug': 'DEBUG: '}.get(
        normalized_level, '')
    return f'{label} {severity}{sanitize_text(message, 0)}'


def _number(value: object) -> float | None:
    """Read a finite numeric observation without coercing booleans or textual placeholders.

    Args:
        value: Candidate numeric field.

    Returns:
        Finite float, or None if the field cannot be displayed as an observation.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _duration(value: object) -> str:
    """Format an observed nonnegative duration.

    Args:
        value: Duration in seconds.

    Returns:
        Parenthesized duration, or empty text when unavailable.
    """
    seconds = _number(value)
    return f' ({seconds:.1f} s)' if seconds is not None and seconds >= 0 else ''


def _progress(payload: Mapping[str, Any]) -> str:
    """Render a one-based logical step counter only when both fields are valid.

    Args:
        payload: Status fields containing zero-based step and total.

    Returns:
        Counter prefix such as [1/5], or an empty string.
    """
    step, total = payload.get('step'), payload.get('total')
    if (isinstance(step, int) and not isinstance(step, bool)
            and isinstance(total, int) and not isinstance(total, bool)
            and 0 <= step < total):
        return f'[{step + 1}/{total}] '
    return ''


def _action_text(action: object, target: object = '', *, past: bool = False,
                 plan: bool = False) -> str:
    """Translate a primitive action into a sentence without claiming physical contact.

    Args:
        action: Primitive action name.
        target: Grounded waypoint, object label, or spoken text.
        past: Whether to describe controller/sequence completion.
        plan: Whether to use imperative plan labels rather than active progress.

    Returns:
        Human-readable action description.
    """
    kind, label = sanitize_text(action).lower(), sanitize_text(target)
    if past:
        labels = {
            'navigate': f'Navigation to {label} completed' if label else 'Navigation completed',
            'find': f'Found {label}' if label else 'Target found',
            'grasp': 'Grasp sequence completed',
            'release': 'Release sequence completed',
            'home': 'Arm home sequence completed',
            'stop': 'Stop completed',
            'speak': 'Speech completed',
        }
    elif plan:
        labels = {'navigate': f'Navigate to {label}', 'find': f'Find {label}',
                  'grasp': 'Grasp', 'release': 'Release', 'home': 'Home arm',
                  'stop': 'Stop', 'speak': f'Say {label}'}
    else:
        labels = {'navigate': f'Navigating to {label}', 'find': f'Searching for {label}',
                  'grasp': 'Grasping target', 'release': 'Releasing object',
                  'home': 'Returning arm home', 'stop': 'Stopping', 'speak': f'Speaking: {label}'}
    return labels.get(kind, f'Action {kind}' if kind else 'Action')


def format_plan(actions: Sequence[Mapping[str, Any]], *, color: bool | None = None) -> str:
    """Render a complete action sequence as a concise plan without a component prefix.

    Args:
        actions: Ordered action dictionaries, without mutation.
        color: Explicit color preference, or None for automatic terminal detection.

    Returns:
        Human labels joined by arrows, or No actions when the plan is empty.
    """
    labels = [_action_text(item.get('action'), item.get('target', ''), plan=True)
              for item in actions if isinstance(item, Mapping)]
    if not labels:
        return 'No actions'
    separator = ' -> '
    if _use_color(color):
        separator = ' \033[2;37m->\033[0m '
    return separator.join(labels)


def error_hint(reason: object, *, target: object = 'object',
               timeout_s: object = None) -> str:
    """Translate known failure codes into actionable operator guidance.

    Args:
        reason: Existing failure reason; machine-readable ROS fields stay unchanged.
        target: Object label used in an acquisition timeout hint.
        timeout_s: Configured search duration, when known.

    Returns:
        A concise explanation and next step, or sanitized original text.
    """
    text = sanitize_text(reason)
    normalized = text.lower().replace('_', ' ')
    if 'navigation status 6' in normalized:
        return '❌ Navigation failed: Robot may be lost. Try 2D Pose Estimate in RViz'
    if 'navigation server discovery timeout' in normalized:
        return '❌ Cannot connect to Nav2. Is Nav2 running?'
    if 'invalid llm response' in normalized:
        if 'fallback rejected' in normalized:
            return '❌ Cannot build a valid plan. Check the command, waypoints and object names.'
        return '⚠️ LLM returned invalid response, using rule-based fallback'
    if ('vision: timeout' in normalized or 'object acquisition timeout' in normalized
            or 'acquisition timeout' in normalized):
        seconds = _number(timeout_s)
        duration = f' within {seconds:g}s' if seconds is not None and seconds > 0 else ''
        return f"❌ Cannot find '{sanitize_text(target)}'{duration}. Is the object visible?"
    if 'no valid depth' in normalized or 'depth unavailable' in normalized:
        return ('⚠️ Object detected but depth unavailable. '
                'Try better lighting or move object to a table.')
    if ('fresh measured arm feedback unavailable' in normalized
            or 'fresh joint feedback required' in normalized
            or 'arm feedback not received' in normalized):
        return '⚠️ Arm feedback not received. Check if arm_status node is running.'
    return text


def _status_message(payload: Mapping[str, Any]) -> tuple[str, str]:
    """Translate one status event into human text and a useful severity.

    Args:
        payload: Machine-readable mission status fields.

    Returns:
        Message text and one of the supported display levels.
    """
    event = sanitize_text(payload.get('event')).lower()
    detail = sanitize_text(payload.get('detail'))
    command = sanitize_text(payload.get('command'))
    reason = sanitize_text(payload.get('error_reason') or payload.get('reason')
                           or payload.get('recovery_reason'))
    if payload.get('action') == 'find' and reason.lower() == 'timeout':
        reason = 'vision: timeout'
    reason = error_hint(reason, target=payload.get('target') or 'object',
                        timeout_s=payload.get('timeout_s'))
    result = sanitize_text(payload.get('result')).lower()
    state = sanitize_text(payload.get('state')).upper()
    if detail.lower().startswith('rejected'):
        return 'Command rejected: ' + detail.partition(':')[2].strip(), 'warning'
    if detail.lower() == 'queued':
        queue = _number(payload.get('queue'))
        waiting = f' ({int(queue)} waiting)' if queue is not None and queue >= 0 else ''
        return f'Queued: {command}{waiting}', 'info'
    if detail.lower() == 'ready':
        return 'Ready for commands', 'success'
    if event == 'mission_started':
        verb = 'Resetting robot' if payload.get('benchmark_reset') else 'Planning'
        return f'{verb}: {command}', 'info'
    if event == 'planning_finished':
        source = sanitize_text(payload.get('planner') or payload.get('source')).lower()
        source_name = {'llm': 'LLM', 'fallback': 'rule-based fallback',
                       'benchmark_reset': 'benchmark reset'}.get(source, source or 'planner')
        milliseconds = _number(payload.get('planning_latency_ms'))
        latency = f' ({milliseconds:.0f} ms)' if milliseconds is not None and (
            milliseconds >= 0) else ''
        message = f'Plan ready: {source_name}{latency}'
        fallback = error_hint(payload.get('fallback_reason') or payload.get('planner_reason'))
        if source == 'fallback' and fallback:
            message += '; ' + fallback
        return message, 'warning' if source == 'fallback' else 'success'
    if event == 'action_started':
        return _progress(payload) + _action_text(
            payload.get('action'), payload.get('target', '')), 'info'
    if event == 'action_finished':
        prefix = _progress(payload)
        if payload.get('success') is True or result == 'succeeded':
            message = prefix + _action_text(payload.get('action'), payload.get('target', ''),
                                            past=True) + _duration(payload.get('duration_s'))
            if payload.get('action') == 'grasp' and not (
                    payload.get('object_contact_verified') is True
                    and payload.get('object_held') is True):
                message += '; object hold unverified'
            return message, 'success'
        action = sanitize_text(payload.get('action')) or 'Action'
        label = 'canceled' if result in ('canceled', 'cancelled') else 'failed'
        message = f'{prefix}{action.capitalize()} {label}'
        if reason:
            message += ': ' + reason
        return message, 'warning' if label == 'canceled' else 'error'
    if event == 'navigation_settling':
        delay = _number(payload.get('delay_s'))
        suffix = f' {delay:g} s' if delay is not None and delay >= 0 else ''
        return f'Navigation reached goal; waiting{suffix} for localization', 'info'
    if event == 'recovery':
        kind = sanitize_text(payload.get('recovery_kind'))
        if kind == 'scan':
            count = _number(payload.get('scan_count'))
            number = f' {int(count)}' if count is not None else ''
            message = f'Scanning for target{number}'
        else:
            count = _number(payload.get('retry_index'))
            number = f' {int(count)}' if count is not None else ''
            delay = _number(payload.get('retry_delay_s'))
            waiting = f' in {delay:g} s' if delay is not None and delay > 0 else ''
            message = f'Retrying{number}{waiting}'
        return message + (': ' + reason if reason else ''), 'warning'
    if event == 'mission_finished' or state in ('DONE', 'FAILED'):
        if detail.lower() == 'stopped':
            return 'Stopped', 'warning'
        if result in ('canceled', 'cancelled'):
            return 'Mission canceled' + (': ' + reason if reason else ''), 'warning'
        if payload.get('success') is not False and result != 'failed' and (
                payload.get('success') is True or result == 'succeeded' or state == 'DONE'):
            return 'Mission complete' + _duration(payload.get('duration_s')), 'success'
        return 'Mission failed' + (': ' + (reason or detail) if reason or detail else ''), 'error'
    states = {'PLANNING': 'Planning', 'WAIT_NAV': 'Navigating', 'WAIT_FIND': 'Searching',
              'WAIT_GRASP': 'Grasp in progress', 'WAIT_MISC': 'Arm operation in progress',
              'NAV_SETTLE': 'Waiting for localization', 'NAV_RETRY_WAIT': 'Waiting to retry',
              'SCAN': 'Scanning', 'IDLE': 'Ready for commands'}
    message = detail or states.get(state, event.replace('_', ' ').capitalize()) or 'Status updated'
    return message, 'info'


def format_status(payload: Mapping[str, Any], *, component: str = 'BRAIN',
                  color: bool | None = None) -> str:
    """Render a mission status while retaining its machine payload for other consumers.

    Args:
        payload: Existing status/event dictionary; never modified by this formatter.
        component: Label displayed before the status.
        color: Explicit color preference, or None for environment/TTY detection.

    Returns:
        A human-readable terminal line without verbose mission/action identifiers.
    """
    message, level = _status_message(payload)
    return format_line(component, message, level, color=color)
