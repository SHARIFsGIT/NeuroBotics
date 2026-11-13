#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for eira_manipulation.pid.PID.

The PID drives the base during grasp alignment, so its numeric contract —
clamping, anti-windup, derivative seeding, reset semantics — is safety
critical. Pure-Python tests, no ROS imports needed.
"""

import pytest

from eira_manipulation.pid import PID


class TestBasics:
    def test_proportional_only(self):
        pid = PID(kp=2.0)
        assert pid.update(0.5, dt=0.1) == pytest.approx(1.0)

    def test_first_update_has_zero_derivative(self):
        # No previous error yet → derivative term is exactly 0.
        pid = PID(kp=0.0, kd=10.0)
        assert pid.update(5.0, dt=0.1) == pytest.approx(0.0)

    def test_second_update_has_derivative(self):
        # Widen the output limits so the raw derivative is not clamped.
        pid = PID(kp=0.0, kd=1.0, output_min=-10.0, output_max=10.0)
        pid.update(0.0, dt=0.1)
        assert pid.update(0.5, dt=0.1) == pytest.approx(5.0)

    def test_zero_dt_returns_zero(self):
        pid = PID(kp=100.0, ki=10.0, kd=10.0)
        assert pid.update(1.0, dt=0.0) == 0.0
        assert pid.update(1.0, dt=-0.5) == 0.0


class TestClamping:
    def test_positive_saturation(self):
        pid = PID(kp=100.0, output_min=-1.0, output_max=1.0)
        assert pid.update(1.0, dt=0.1) == 1.0

    def test_negative_saturation(self):
        pid = PID(kp=100.0, output_min=-1.0, output_max=1.0)
        assert pid.update(-1.0, dt=0.1) == -1.0

    def test_asymmetric_limits(self):
        # Grasp alignment uses a smaller reverse limit (max_rev_vel).
        pid = PID(kp=10.0, output_min=-0.08, output_max=0.15)
        assert pid.update(1.0, dt=0.1) == 0.15
        assert pid.update(-1.0, dt=0.1) == -0.08


class TestAntiWindup:
    def test_integral_is_bounded(self):
        # Sustained error must not integrate past integral_limit.
        pid = PID(kp=0.0, ki=1.0, integral_limit=1.0)
        for _ in range(1000):
            out = pid.update(10.0, dt=0.1)
        assert out == pytest.approx(1.0)  # ki * clamped integral = 1.0

    def test_integral_decays_after_clamp(self):
        pid = PID(kp=0.0, ki=1.0, integral_limit=1.0)
        for _ in range(100):
            pid.update(10.0, dt=0.1)      # wind up to the clamp (out = 1.0)
        # Small reverse error: integral 1.0 - 0.1 = 0.9 → output decays.
        assert pid.update(-1.0, dt=0.1) == pytest.approx(0.9)


class TestReset:
    def test_reset_forgets_history(self):
        pid = PID(kp=1.0, ki=1.0, kd=1.0)
        pid.update(2.0, dt=0.1)
        pid.update(2.0, dt=0.1)
        pid.reset()
        # Without reset: integral 0.4 + 0.05 and derivative (0.5-2)/0.1 = -15
        # would give a clamped -1.0. With reset: P 0.5 + I 0.05 + D 0 = 0.55
        # — this value proves BOTH the integral and the previous error were
        # actually cleared.
        assert pid.update(0.5, dt=0.1) == pytest.approx(0.55)
