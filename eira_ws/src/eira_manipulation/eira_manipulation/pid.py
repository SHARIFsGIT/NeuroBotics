"""Provide bounded SI-unit PID for the E-AIRA base alignment stage.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro mecanum base / Jetson Orin NX.
"""

import math


class PID:
    """Discrete PID with integral clamping and finite bounded output."""

    def __init__(self, kp: float, ki: float = 0.0, kd: float = 0.0,
                 output_min: float = -1.0, output_max: float = 1.0,
                 integral_limit: float = 1.0) -> None:
        """Configure controller gains and limits.

        Args:
            kp: Proportional gain.
            ki: Integral gain.
            kd: Derivative gain.
            output_min: Smallest allowed output.
            output_max: Largest allowed output.
            integral_limit: Absolute integral accumulator limit.

        Raises:
            ValueError: Gains or ordered limits are invalid.
        """
        values = (kp, ki, kd, output_min, output_max, integral_limit)
        if (not all(math.isfinite(float(v)) for v in values)
                or output_min > output_max or integral_limit < 0):
            raise ValueError('PID requires finite gains and ordered limits')
        self.kp, self.ki, self.kd = float(kp), float(ki), float(kd)
        self.output_min, self.output_max = float(output_min), float(output_max)
        self.integral_limit = float(integral_limit)
        self._integral = 0.0
        self._previous_error: float | None = None

    def reset(self) -> None:
        """Forget accumulated error and derivative history before a new target."""
        self._integral = 0.0
        self._previous_error = None

    def update(self, error: float, dt: float) -> float:
        """Advance one PID step.

        Args:
            error: Finite position or bearing error in SI units.
            dt: Elapsed seconds; nonpositive intervals return zero.

        Returns:
            Clamped control output.

        Raises:
            ValueError: Error or interval is nonfinite.
        """
        if not math.isfinite(error) or not math.isfinite(dt):
            raise ValueError('PID error and interval must be finite')
        if dt <= 0.0:
            return 0.0
        self._integral = max(-self.integral_limit,
                             min(self.integral_limit, self._integral + error * dt))
        derivative = 0.0 if self._previous_error is None else (
            error - self._previous_error) / dt
        self._previous_error = error
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(self.output_min, min(self.output_max, output))
