"""Package support for E-AIRA manipulation.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX.
"""

import pytest

from eira_manipulation.pid import PID


class TestBasics:
    """Group related PID controller invariants."""
    def test_proportional_only(self) -> None:
        """Verify proportional only."""
        pid = PID(kp=2.0)
        assert pid.update(0.5, dt=0.1) == pytest.approx(1.0)

    def test_first_update_has_zero_derivative(self) -> None:
        """Verify first update has zero derivative."""
        # No previous error yet → derivative term is exactly 0.
        pid = PID(kp=0.0, kd=10.0)
        assert pid.update(5.0, dt=0.1) == pytest.approx(0.0)

    def test_second_update_has_derivative(self) -> None:
        """Verify second update has derivative."""
        # Widen the output limits so the raw derivative is not clamped.
        pid = PID(kp=0.0, kd=1.0, output_min=-10.0, output_max=10.0)
        pid.update(0.0, dt=0.1)
        assert pid.update(0.5, dt=0.1) == pytest.approx(5.0)

    def test_zero_dt_returns_zero(self) -> None:
        """Verify zero dt returns zero."""
        pid = PID(kp=100.0, ki=10.0, kd=10.0)
        assert pid.update(1.0, dt=0.0) == 0.0
        assert pid.update(1.0, dt=-0.5) == 0.0


class TestClamping:
    """Group related PID controller invariants."""
    def test_positive_saturation(self) -> None:
        """Verify positive saturation."""
        pid = PID(kp=100.0, output_min=-1.0, output_max=1.0)
        assert pid.update(1.0, dt=0.1) == 1.0

    def test_negative_saturation(self) -> None:
        """Verify negative saturation."""
        pid = PID(kp=100.0, output_min=-1.0, output_max=1.0)
        assert pid.update(-1.0, dt=0.1) == -1.0

    def test_asymmetric_limits(self) -> None:
        """Verify asymmetric limits."""
        # Grasp alignment uses a smaller reverse limit (max_rev_vel).
        pid = PID(kp=10.0, output_min=-0.08, output_max=0.15)
        assert pid.update(1.0, dt=0.1) == 0.15
        assert pid.update(-1.0, dt=0.1) == -0.08


class TestAntiWindup:
    """Group related PID controller invariants."""
    def test_integral_is_bounded(self) -> None:
        """Verify integral is bounded."""
        # Sustained error must not integrate past integral_limit.
        pid = PID(kp=0.0, ki=1.0, integral_limit=1.0)
        for _ in range(1000):
            out = pid.update(10.0, dt=0.1)
        assert out == pytest.approx(1.0)  # ki * clamped integral = 1.0

    def test_integral_decays_after_clamp(self) -> None:
        """Verify integral decays after clamp."""
        pid = PID(kp=0.0, ki=1.0, integral_limit=1.0)
        for _ in range(100):
            pid.update(10.0, dt=0.1)      # wind up to the clamp (out = 1.0)
        # Small reverse error: integral 1.0 - 0.1 = 0.9 → output decays.
        assert pid.update(-1.0, dt=0.1) == pytest.approx(0.9)


class TestReset:
    """Group related PID controller invariants."""
    def test_reset_forgets_history(self) -> None:
        """Verify reset forgets history."""
        pid = PID(kp=1.0, ki=1.0, kd=1.0)
        pid.update(2.0, dt=0.1)
        pid.update(2.0, dt=0.1)
        pid.reset()
        # Without reset: integral 0.4 + 0.05 and derivative (0.5-2)/0.1 = -15
        # would give a clamped -1.0. With reset: P 0.5 + I 0.05 + D 0 = 0.55
        # — this value proves BOTH the integral and the previous error were
        # actually cleared.
        assert pid.update(0.5, dt=0.1) == pytest.approx(0.55)
