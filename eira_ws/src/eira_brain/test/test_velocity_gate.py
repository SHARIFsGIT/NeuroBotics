"""Regression tests for command arbitration and independent watchdog timing.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX (hardware-free tests).
"""

from unittest.mock import Mock, patch

import pytest
from geometry_msgs.msg import Twist

from eira_brain.safety_monitor import SafetyMonitor
from eira_brain.velocity_gate import GatePolicy


def policy() -> GatePolicy:
    """Return an authorized policy whose last Brain heartbeat is at time ten."""
    gate = GatePolicy()
    gate.heartbeat = 10.0
    gate.select('arm', 10.0)
    gate.put('arm', (0.1, 0.0, 0.0), 10.0)
    return gate


def test_selected_source_only() -> None:
    """An unselected source cannot override the active controller."""
    gate = policy()
    gate.put('nav', (0.2, 0.0, 1.0), 10.1)
    assert gate.output(10.2)[0] == (0.1, 0.0, 0.0)


def test_expired_command_stops_while_brain_alive() -> None:
    """A held final Twist cannot remain active beyond its source lease."""
    assert policy().output(10.6)[0] == (0.0, 0.0, 0.0)


def test_heartbeat_loss_revokes_lease() -> None:
    """Even a still-publishing controller stops when Brain liveness expires."""
    gate = policy()
    gate.put('arm', (0.1, 0.0, 0.0), 15.1)
    assert gate.output(15.2)[1] == 'heartbeat_stale'
    assert gate.owner == 'none'
    gate.heartbeat = 15.3
    assert gate.output(15.3)[0] == (0.0, 0.0, 0.0)


def test_switch_discards_previous_source_commands() -> None:
    """Changing stages requires a command produced after the change."""
    gate = policy()
    gate.select('nav', 10.1)
    assert gate.output(10.2)[0] == (0.0, 0.0, 0.0)


def test_stop_overrides_fresh_commands() -> None:
    """A safety interlock always dominates a live source and heartbeat."""
    gate = policy()
    gate.safety_stop = True
    assert gate.output(10.1)[1] == 'safety_stop'
    assert gate.owner == 'none'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_commands_rejected(value: float) -> None:
    """Nonfinite actuator commands never enter the source cache."""
    with pytest.raises(ValueError):
        policy().put('arm', (value, 0.0, 0.0), 10.0)


def test_edge_clearance_must_be_fresh() -> None:
    """An expired clear observation cannot authorize driving over unknown floor."""
    gate = policy()
    gate.require_edge = True
    gate.edge_blocked = False
    gate.edge_stamp = 8.0
    assert gate.output(10.1)[1] == 'edge_blocked_or_stale'


def test_watchdog_covers_last_motion_before_timeout() -> None:
    """The old two-second motion-window gap cannot suppress intervention."""
    node = object.__new__(SafetyMonitor)
    node._timeout = 5.0
    node._grace = 0.0
    node._last_heartbeat = 0.0
    node._last_motion = 0.0
    node._started_at = 0.0
    node._intervening = False
    node._stop_pub = Mock()
    node._cmd_vel_pub = Mock()
    node._emit = Mock()
    with patch('eira_brain.safety_monitor.time.monotonic', return_value=6.0):
        node._check()
    assert node._stop_pub.publish.call_args.args[0].data is True
    assert isinstance(node._cmd_vel_pub.publish.call_args.args[0], Twist)
    node._emit.assert_called_once_with('brain_heartbeat_lost')


def test_stop_rejects_delayed_ownership_from_same_mission() -> None:
    """A queued ownership renewal cannot undo a stop from another topic."""
    import json
    from std_msgs.msg import String
    from eira_brain.velocity_gate import VelocityGate
    node = object.__new__(VelocityGate)
    node.policy = policy()
    node._context = {'mission_id': 'stopped-mission', 'action_id': 'align'}
    node._revoked_missions = set()
    node._publisher = Mock()
    node._events = Mock()
    node._on_command(String(data='stop'))
    node._on_owner(String(data=json.dumps({
        'owner': 'arm', 'mission_id': 'stopped-mission', 'action_id': 'align'})))
    assert node.policy.owner == 'none'
    node._on_owner(String(data=json.dumps({
        'owner': 'nav', 'mission_id': 'new-mission', 'action_id': 'navigate'})))
    assert node.policy.owner == 'nav'


def test_safety_revocation_event_retains_mission_identity() -> None:
    """The Brain can attribute a revoked lease to the active mission."""
    import json
    from eira_brain.velocity_gate import VelocityGate
    node = object.__new__(VelocityGate)
    node.policy = policy()
    node._context = {'mission_id': 'unsafe-mission', 'action_id': 'align'}
    node._revoked_missions = set()
    node._publisher = Mock()
    node._events = Mock()
    node._revoke('edge_blocked_or_stale')
    event = json.loads(node._events.publish.call_args.args[0].data)
    assert event['mission_id'] == 'unsafe-mission'
    assert event['action_id'] == 'align'
    assert event['event'] == 'edge_blocked_or_stale'
    assert node.policy.owner == 'none'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), 0.0, -1.0])
def test_invalid_command_expiration_rejected(value: float) -> None:
    """Nonfinite leases cannot disable the command watchdog.

    Args:
        value: Invalid timeout.
    """
    with pytest.raises(ValueError):
        GatePolicy(command_timeout=value)


def test_initial_heartbeat_discovery_waits_at_zero_without_revoking() -> None:
    """A late first heartbeat may enable a fresh source without aborting startup."""
    gate = GatePolicy()
    gate.select('nav', 10.0)
    gate.put('nav', (0.1, 0.0, 0.0), 10.1)
    assert gate.output(10.2) == ((0.0, 0.0, 0.0), 'heartbeat_pending')
    assert gate.owner == 'nav'
    gate.heartbeat = 10.3
    assert gate.output(10.3)[0] == (0.1, 0.0, 0.0)
    gate.heartbeat = None
    assert gate.output(15.1)[1] == 'heartbeat_stale'
    assert gate.owner == 'none'
