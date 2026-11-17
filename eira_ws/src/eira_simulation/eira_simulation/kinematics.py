"""Compute bounded numerical kinematics from the actual exercise-08 M3 Pro URDF.

Author: E-AIRA maintainers.
Hardware target: Gazebo M3 Pro simulation / ROS 2 Humble, Python 3.10.
This is a simulation adapter, not a replacement Yahboom hardware IK driver.
Position-only IK is the default; an underactuated arm cannot satisfy arbitrary 6-D poses.
"""

from dataclasses import dataclass
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np


ARM_JOINTS = tuple(f'arm{i}_Joint' for i in range(1, 6))
FINGER_JOINTS = ('rlink1_Joint', 'rlink2_Joint', 'llink1_Joint',
                 'llink2_Joint', 'rlink3_Joint', 'llink3_Joint')
FINGER_SIGNS = (1, 1, 1, -1, -1, 1)


class KinematicsError(RuntimeError):
    """Report an unreachable/malformed simulation IK request without fabricating joint angles."""


def rotation_rpy(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Return the URDF fixed-axis Rz(yaw) Ry(pitch) Rx(roll) rotation matrix."""
    sr, cr, sp, cp, sy, cy = (math.sin(roll), math.cos(roll), math.sin(pitch),
                              math.cos(pitch), math.sin(yaw), math.cos(yaw))
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]], dtype=float)


def axis_rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    """Return a Rodrigues rotation about one normalized URDF joint axis."""
    norm = float(np.linalg.norm(axis))
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError('joint axis must be finite and nonzero')
    x, y, z = axis / norm
    cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]], dtype=float)
    return np.eye(3) + math.sin(angle) * cross + (1.0 - math.cos(angle)) * (cross @ cross)


def rotation_vector(matrix: np.ndarray) -> np.ndarray:
    """Return a stable rotation residual for finite-difference orientation IK."""
    cosine = float(np.clip((np.trace(matrix) - 1.0) / 2.0, -1.0, 1.0))
    angle = math.acos(cosine)
    skew = np.array([matrix[2, 1] - matrix[1, 2], matrix[0, 2] - matrix[2, 0],
                     matrix[1, 0] - matrix[0, 1]]) / 2.0
    sine = float(np.linalg.norm(skew))
    if angle < 1e-8:
        return skew
    if sine > 1e-7:
        return skew * angle / sine
    # A pi rotation has zero skew; its unit eigenvector still identifies its axis.
    values, vectors = np.linalg.eig(matrix)
    axis = np.real(vectors[:, int(np.argmin(np.abs(values - 1.0)))])
    return axis / np.linalg.norm(axis) * angle


def _vector(text: str, count: int = 3) -> np.ndarray:
    """Parse a finite URDF vector with an explicit expected dimension."""
    value = np.asarray([float(item) for item in text.split()], dtype=float)
    if value.size != count or not np.isfinite(value).all():
        raise ValueError('invalid finite URDF vector')
    return value


@dataclass
class ChainJoint:
    """Store one parsed URDF transform and its original motion limits."""

    name: str
    kind: str
    parent: str
    child: str
    origin: np.ndarray
    axis: np.ndarray
    lower: float
    upper: float
    velocity: float


@dataclass
class IKResult:
    """Describe convergence explicitly, including residuals and solved joint values."""

    success: bool
    positions: dict[str, float]
    position_error_m: float
    orientation_error_rad: float
    iterations: int


class URDFChain:
    """Extract a topological base-to-tool chain and solve damped numerical IK."""

    def __init__(self, xml: str, base_link: str = 'base_link',
                 tip_link: str = 'Gripping') -> None:
        """Parse the actual model rather than assuming generic link lengths or axes.

        Args:
            xml: Expanded URDF XML.
            base_link: Reference frame of requested target positions.
            tip_link: Tool link whose pose the solver controls.

        Raises:
            ValueError: The chain, limits, or transform vectors are malformed.
            ET.ParseError: XML is invalid.
        """
        root = ET.fromstring(xml)
        self.all_joints: dict[str, ChainJoint] = {}
        by_child = {}
        for element in root.findall('joint'):
            kind = element.get('type', '')
            if kind not in ('fixed', 'revolute', 'continuous', 'prismatic'):
                raise ValueError(f'unsupported URDF joint type: {kind}')
            origin = np.eye(4)
            spec = element.find('origin')
            if spec is not None:
                origin[:3, 3] = _vector(spec.get('xyz', '0 0 0'))
                origin[:3, :3] = rotation_rpy(*_vector(spec.get('rpy', '0 0 0')))
            axis_spec = element.find('axis')
            axis = _vector(axis_spec.get('xyz', '1 0 0') if axis_spec is not None else '1 0 0')
            if np.linalg.norm(axis) == 0:
                raise ValueError('zero URDF joint axis')
            axis /= np.linalg.norm(axis)
            limits = element.find('limit')
            lower, upper, velocity = -math.pi, math.pi, 1.0
            if kind in ('revolute', 'prismatic'):
                if limits is None:
                    raise ValueError('bounded joints require URDF limits')
                lower, upper = float(limits.attrib['lower']), float(limits.attrib['upper'])
            if limits is not None:
                velocity = float(limits.get('velocity', '1.0'))
            if not all(math.isfinite(v) for v in (lower, upper, velocity)) or lower > upper:
                raise ValueError('invalid URDF joint limits')
            parent, child = element.find('parent'), element.find('child')
            if parent is None or child is None:
                raise ValueError('joint must identify parent and child links')
            joint = ChainJoint(element.attrib['name'], kind, parent.attrib['link'],
                               child.attrib['link'], origin, axis, lower, upper, velocity)
            if joint.child in by_child or joint.name in self.all_joints:
                raise ValueError('URDF must define a tree with unique joint names')
            by_child[joint.child] = joint
            self.all_joints[joint.name] = joint
        reverse = []
        cursor, visited = tip_link, set()
        while cursor != base_link:
            if cursor in visited or cursor not in by_child:
                raise ValueError(f'no acyclic chain from {base_link} to {tip_link}')
            visited.add(cursor)
            joint = by_child[cursor]
            reverse.append(joint)
            cursor = joint.parent
        self.joints = list(reversed(reverse))
        self.movable = [joint for joint in self.joints if joint.kind != 'fixed']
        if not self.movable:
            raise ValueError('IK chain must contain at least one movable joint')

    @classmethod
    def from_file(cls, path: Path, base_link: str = 'base_link',
                  tip_link: str = 'Gripping') -> 'URDFChain':
        """Load one expanded URDF model from a file.

        Args:
            path: Expanded model path.
            base_link: Target coordinate frame.
            tip_link: Tool endpoint frame.

        Returns:
            Parsed chain.

        Raises:
            OSError: The file cannot be read.
            ValueError: The chain is malformed.
        """
        return cls(path.read_text(encoding='utf-8'), base_link, tip_link)

    def forward(self, positions: dict[str, float]) -> np.ndarray:
        """Compute the base-to-tool homogeneous transform for finite, bounded joint positions.

        Args:
            positions: URDF joint-name to radian/metre position mapping.

        Returns:
            Tool's 4x4 transform in the configured base frame.

        Raises:
            ValueError: A supplied position is nonfinite or outside URDF limits.
        """
        transform = np.eye(4)
        for joint in self.joints:
            value = float(positions.get(joint.name, 0.0))
            if not math.isfinite(value):
                raise ValueError('nonfinite joint position')
            if joint.kind != 'fixed' and not joint.lower - 1e-8 <= value <= joint.upper + 1e-8:
                raise ValueError(f'{joint.name} exceeds URDF limits')
            transform = transform @ joint.origin
            motion = np.eye(4)
            if joint.kind in ('revolute', 'continuous'):
                motion[:3, :3] = axis_rotation(joint.axis, value)
            elif joint.kind == 'prismatic':
                motion[:3, 3] = joint.axis * value
            transform = transform @ motion
        return transform

    def inverse(self, target: np.ndarray, seed: dict[str, float] | None = None,
                active_names: tuple[str, ...] | None = None,
                extra_limits: dict[str, tuple[float, float]] | None = None,
                orientation: np.ndarray | None = None, orientation_weight: float = 0.0,
                tolerance_m: float = 0.005, orientation_tolerance_rad: float = 0.15,
                max_iterations: int = 100, max_seconds: float = 0.2,
                damping: float = 0.02, epsilon: float = 1e-5,
                max_step_rad: float = 0.15, restarts: int = 3,
                random_seed: int = 42) -> IKResult:
        """Solve bounded IK with finite-difference damped least squares and a wall deadline.

        Args:
            target: Desired three-dimensional position in metres.
            seed: Measured starting joint positions, when available.
            active_names: Joints allowed to move; other chain joints retain their seed.
            extra_limits: Additional software limits intersected with URDF bounds.
            orientation: Optional desired 3x3 rotation matrix.
            orientation_weight: Orientation residual weight; zero means position only.
            tolerance_m: Required position residual.
            orientation_tolerance_rad: Required rotation residual when orientation is enabled.
            max_iterations: Iteration limit per restart.
            max_seconds: Total wall-clock solve deadline.
            damping: Positive damped-least-squares regularization.
            epsilon: Finite-difference displacement.
            max_step_rad: Per-update joint step cap.
            restarts: Number of bounded deterministic multistart attempts.
            random_seed: Local RNG seed for repeatable additional seeds.

        Returns:
            Best bounded solution and explicit convergence/residual fields.

        Raises:
            ValueError: Target, limits, or solver configuration is invalid.
        """
        target = np.asarray(target, dtype=float)
        if target.shape != (3,) or not np.isfinite(target).all():
            raise ValueError('IK target must be a finite 3-vector')
        if (min(tolerance_m, max_seconds, damping, epsilon, max_step_rad) <= 0
                or max_iterations < 1 or restarts < 1 or orientation_weight < 0):
            raise ValueError('invalid IK solver bounds')
        if not all(math.isfinite(v) for v in (tolerance_m, max_seconds, damping, epsilon,
                                              max_step_rad, orientation_weight)):
            raise ValueError('IK solver bounds must be finite')
        use_orientation = orientation is not None and orientation_weight > 0
        if use_orientation:
            orientation = np.asarray(orientation, dtype=float)
            if orientation.shape != (3, 3) or not np.isfinite(orientation).all():
                raise ValueError('orientation must be a finite 3x3 matrix')
        active = [joint for joint in self.movable
                  if active_names is None or joint.name in active_names]
        if not active:
            raise ValueError('no movable IK joints selected')
        limits = extra_limits or {}
        lower = np.array([max(j.lower, limits.get(j.name, (j.lower, j.upper))[0]) for j in active])
        upper = np.array([min(j.upper, limits.get(j.name, (j.lower, j.upper))[1]) for j in active])
        if np.any(lower > upper):
            raise ValueError('software and URDF joint limits do not intersect')
        baseline = {j.name: float((seed or {}).get(j.name, 0.0)) for j in self.movable}
        for joint in self.movable:
            baseline[joint.name] = float(np.clip(baseline[joint.name], joint.lower, joint.upper))
        initial = np.clip([baseline[j.name] for j in active], lower, upper)
        rng = np.random.default_rng(random_seed)
        started = time.monotonic()
        best = IKResult(False, dict(baseline), math.inf, math.inf, 0)
        total_iterations = 0
        for attempt in range(restarts):
            q = initial.copy() if attempt == 0 else rng.uniform(lower, upper)
            for _ in range(max_iterations):
                if time.monotonic() - started >= max_seconds:
                    return best
                total_iterations += 1
                positions = dict(baseline, **{j.name: float(v) for j, v in zip(active, q)})
                current = self.forward(positions)
                position_error = target - current[:3, 3]
                rotation_error = (rotation_vector(orientation @ current[:3, :3].T)
                                  if use_orientation else np.zeros(3))
                pos_norm, rot_norm = float(np.linalg.norm(position_error)), float(
                    np.linalg.norm(rotation_error))
                score = pos_norm + orientation_weight * rot_norm
                best_score = (best.position_error_m
                              + orientation_weight * best.orientation_error_rad)
                if not math.isfinite(best_score) or score < best_score:
                    best = IKResult(False, positions, pos_norm, rot_norm, total_iterations)
                if pos_norm <= tolerance_m and (not use_orientation
                                                or rot_norm <= orientation_tolerance_rad):
                    return IKResult(True, positions, pos_norm, rot_norm, total_iterations)
                error = np.concatenate((position_error, orientation_weight * rotation_error))
                jacobian = np.zeros((6, len(active)))
                for index, joint in enumerate(active):
                    direction = epsilon if q[index] + epsilon <= upper[index] else -epsilon
                    if q[index] + direction < lower[index]:
                        continue
                    perturbed = dict(positions)
                    perturbed[joint.name] += direction
                    moved = self.forward(perturbed)
                    jacobian[:3, index] = (moved[:3, 3] - current[:3, 3]) / direction
                    if use_orientation:
                        jacobian[3:, index] = orientation_weight * rotation_vector(
                            moved[:3, :3] @ current[:3, :3].T) / direction
                update = jacobian.T @ np.linalg.solve(
                    jacobian @ jacobian.T + damping ** 2 * np.eye(6), error)
                q = np.clip(q + np.clip(update, -max_step_rad, max_step_rad), lower, upper)
        return best


def servo_to_joints(angles: list[float], offsets: list[float], signs: list[float],
                    gripper_open_deg: float = 90.0, gripper_close_deg: float = 30.0,
                    gripper_open_rad: float = 0.0, gripper_close_rad: float = -1.0
                    ) -> dict[str, float]:
    """Map the existing six-servo degree commands to the actual URDF arm/finger joints.

    Args:
        angles: Six existing Yahboom servo angles in degrees.
        offsets: Five servo zero offsets in degrees.
        signs: Five direction multipliers, each +1 or -1.
        gripper_open_deg: Open servo reference.
        gripper_close_deg: Closed servo reference.
        gripper_open_rad: Open finger coupling position.
        gripper_close_rad: Closed finger coupling position inside the actual URDF limits.

    Returns:
        All five arm and six coupled gripper joint positions.

    Raises:
        ValueError: Servo/calibration data is malformed or nonfinite.
    """
    if len(angles) != 6 or len(offsets) != 5 or len(signs) != 5:
        raise ValueError('six servo angles and five offsets/signs are required')
    calibration = [*angles, *offsets, *signs, gripper_open_deg, gripper_close_deg,
                   gripper_open_rad, gripper_close_rad]
    if (not all(math.isfinite(v) for v in calibration)
            or any(sign not in (-1.0, 1.0) for sign in signs)
            or any(not 0 <= value <= 180 for value in angles)
            or gripper_close_deg == gripper_open_deg):
        raise ValueError('invalid servo mapping calibration')
    positions = {name: math.radians(angle - offset) * sign
                 for name, angle, offset, sign in zip(ARM_JOINTS, angles[:5], offsets, signs)}
    ratio = np.clip((angles[5] - gripper_open_deg) / (gripper_close_deg - gripper_open_deg), 0, 1)
    coupled = float(gripper_open_rad + ratio * (gripper_close_rad - gripper_open_rad))
    positions.update({name: coupled * sign for name, sign in zip(FINGER_JOINTS, FINGER_SIGNS)})
    return positions


def joints_to_servo(positions: dict[str, float], offsets: list[float], signs: list[float],
                    gripper_open_deg: float = 90.0, gripper_close_deg: float = 30.0,
                    gripper_open_rad: float = 0.0,
                    gripper_close_rad: float = -1.0) -> list[float]:
    """Convert measured URDF positions back to six servo degree readings.

    Args:
        positions: Measured positions for all arm joints and the first finger joint.
        offsets: Five degree-valued zero offsets.
        signs: Five direction multipliers.
        gripper_open_deg: Open servo reference.
        gripper_close_deg: Closed servo reference.
        gripper_open_rad: Open model position.
        gripper_close_rad: Closed model position.

    Returns:
        Measured equivalent servo angles, never desired-command substitutes.

    Raises:
        ValueError: Calibration or measurements are nonfinite/incomplete.
    """
    required = (*ARM_JOINTS, FINGER_JOINTS[0])
    if len(offsets) != 5 or len(signs) != 5 or any(name not in positions for name in required):
        raise ValueError('complete measured arm/gripper positions are required')
    if gripper_close_rad == gripper_open_rad or any(sign not in (-1.0, 1.0) for sign in signs):
        raise ValueError('invalid inverse servo calibration')
    values = [math.degrees(positions[name]) / sign + offset
              for name, sign, offset in zip(ARM_JOINTS, signs, offsets)]
    ratio = ((positions[FINGER_JOINTS[0]] - gripper_open_rad)
             / (gripper_close_rad - gripper_open_rad))
    values.append(gripper_open_deg + ratio * (gripper_close_deg - gripper_open_deg))
    if not all(math.isfinite(value) for value in values):
        raise ValueError('measured servo equivalents must be finite')
    return values
