"""Apply reproducible metric depth noise without inventing valid returns.

Author: E-AIRA maintainers.
Hardware target: Dabai RGB-D contract / ROS 2 Humble Gazebo Classic.
"""

import math

import numpy as np
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


def noisy_depth(depth: np.ndarray, sigma: float, generator: np.random.Generator) -> np.ndarray:
    """Add zero-mean metric noise only to existing positive finite depth samples.

    Args:
        depth: Floating-point metre-valued input image.
        sigma: Noise standard deviation in metres.
        generator: Seeded experiment RNG.
    Returns:
        Float32 image preserving zero/NaN invalid samples.
    Raises:
        ValueError: If dimensions or noise parameters are invalid.
    """
    if depth.ndim != 2 or not math.isfinite(sigma) or sigma < 0:
        raise ValueError('expected a depth plane and finite nonnegative sigma')
    output = depth.astype(np.float32, copy=True)
    valid = np.isfinite(output) & (output > 0)
    output[valid] += generator.normal(0.0, sigma, int(np.count_nonzero(valid)))
    output[valid & (output <= 0)] = np.nan
    return output


class DepthNoise(Node):
    """Bridge Gazebo raw depth to the public registered-depth topic."""

    def __init__(self) -> None:
        """Initialize the local seeded RNG and sensor-data interfaces."""
        super().__init__('sim_depth_noise')
        self.declare_parameter('seed', 0)
        self.declare_parameter('depth_noise_stddev_m', 0.002)
        self._sigma = float(self.get_parameter('depth_noise_stddev_m').value)
        if not math.isfinite(self._sigma) or self._sigma < 0:
            raise ValueError('depth_noise_stddev_m must be finite and nonnegative')
        self._rng = np.random.default_rng(int(self.get_parameter('seed').value))
        self._bridge = CvBridge()
        self._publisher = self.create_publisher(Image, '/camera/depth/image_raw',
                                                qos_profile_sensor_data)
        self.create_subscription(Image, '/eira/sim/depth_raw', self._on_image,
                                 qos_profile_sensor_data)

    def _on_image(self, message: Image) -> None:
        """Perturb a valid depth frame while retaining its measurement timestamp.

        Args:
            message: Gazebo float32 metre image.
        """
        try:
            depth = self._bridge.imgmsg_to_cv2(message, desired_encoding='passthrough')
            if depth.dtype == np.uint16:
                depth = depth.astype(np.float32) / 1000.0
            output = self._bridge.cv2_to_imgmsg(noisy_depth(depth, self._sigma, self._rng),
                                                encoding='32FC1')
            output.header = message.header
            self._publisher.publish(output)
        except (CvBridgeError, ValueError, TypeError) as exc:
            self.get_logger().warning(f'depth noise frame rejected: {exc}',
                                      throttle_duration_sec=5.0)


def main(args: list[str] | None = None) -> None:
    """Run the simulated sensor adapter.

    Args:
        args: Optional ROS arguments.
    """
    rclpy.init(args=args)
    node = DepthNoise()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
