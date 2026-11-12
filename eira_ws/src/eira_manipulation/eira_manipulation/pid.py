#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pid.py — minimal PID controller with anti-windup and output clamping.

The gains default to the values proven on this robot by the deep-tracking
node (folder 32): linear ``(0.5, 0.0, 0.1)`` and angular ``(0.5, 0.0, 0.3)``.
That node feeds its angular gains divided by 100 to its controller (they are
tuned "in percent" in the Yahboom convention); here the division is applied
once in the parameter defaults, so the stored parameters remain in the
familiar 0-100 convention of the original code.
"""


class PID:
    """Discrete PID with integral clamping and bounded output."""

    def __init__(self, kp: float, ki: float = 0.0, kd: float = 0.0,
                 output_min: float = -1.0, output_max: float = 1.0,
                 integral_limit: float = 1.0):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.output_min = float(output_min)
        self.output_max = float(output_max)
        self.integral_limit = float(integral_limit)

        self._integral = 0.0
        self._previous_error = None

    def reset(self):
        """Forget history — call when the controlled target changes."""
        self._integral = 0.0
        self._previous_error = None

    def update(self, error: float, dt: float) -> float:
        """One PID step; ``dt`` seconds since the previous update."""
        if dt <= 0.0:
            return 0.0

        self._integral = max(
            -self.integral_limit,
            min(self.integral_limit, self._integral + error * dt))

        derivative = 0.0
        if self._previous_error is not None:
            derivative = (error - self._previous_error) / dt
        self._previous_error = error

        output = (self.kp * error
                  + self.ki * self._integral
                  + self.kd * derivative)
        return max(self.output_min, min(self.output_max, output))
