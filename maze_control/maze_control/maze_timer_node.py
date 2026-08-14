#!/usr/bin/env python3
"""
maze_timer_node.py

Watches the robot's odometry. When its estimated world-frame pose enters
the finish-line region (the checkered pattern around x=5, y=2.5), it:
  1. records elapsed time since this node started,
  2. logs + publishes a congratulations message to /maze_timer/status,
  3. shuts the whole simulation down (Gazebo, bridge, everything).

Position estimate: /odom reports pose relative to wherever the robot was
SPAWNED, not world-absolute. This node adds spawn_x/spawn_y (should match
the -x/-y given to `ros_gz_sim create` in the launch file) to approximate
world-frame position. That's a coarse estimate - fine for "did it cross
into the finish region", not for precision localization.

/maze_timer/status (std_msgs/String) is bridged to a gz-side topic of the
same name (see bridge_config.yaml) so it can be displayed live inside the
Gazebo GUI using the stock "Topic Echo" plugin - see the launch/GUI setup
notes for how to dock that panel to the top-left. This node does NOT
touch the SDF <gui> block: overriding it in the world file replaces
Gazebo's entire default plugin stack (3D view included), which is a much
riskier change than adding a panel through the GUI's own plugin picker.

Shutdown: this node calls rclpy.shutdown() and exits after finishing. On
its own, that only stops this one process - the launch file registers an
OnProcessExit handler keyed to this node's process that issues a full
launch Shutdown() when it exits, which is what actually tears down
Gazebo + the bridge + the wall service alongside it.
"""

import time

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import String

import sys


class MazeTimerNode(Node):

    def __init__(self):
        super().__init__('maze_timer_node')

        self.declare_parameter('spawn_x', 0.5)
        self.declare_parameter('spawn_y', 0.5)
        # Finish region matches the checkered finish line: x in [4.7,5.3],
        # y in [1.95,3.0]. finish_x is intentionally a bit inside that so
        # the robot has to actually be on the pattern, not just approaching it.
        self.declare_parameter('finish_x', 4.5)
        self.declare_parameter('finish_y_min', 1.95)
        self.declare_parameter('finish_y_max', 3.0)
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('status_period', 0.5)  # live "elapsed" tick rate

        self._spawn_x = self.get_parameter('spawn_x').value
        self._spawn_y = self.get_parameter('spawn_y').value
        self._finish_x = self.get_parameter('finish_x').value
        self._finish_y_min = self.get_parameter('finish_y_min').value
        self._finish_y_max = self.get_parameter('finish_y_max').value

        self._start_time = time.monotonic()
        self._finished = False

        self._status_pub = self.create_publisher(String, '/maze_timer/status', 10)

        odom_topic = self.get_parameter('odom_topic').value
        self._odom_sub = self.create_subscription(
            Odometry, odom_topic, self._on_odom, 10)

        status_period = self.get_parameter('status_period').value
        self._status_timer = self.create_timer(status_period, self._publish_ticking_status)

        self.get_logger().info(
            f"maze_timer_node watching '{odom_topic}', finish region "
            f"x>={self._finish_x}, y in [{self._finish_y_min}, {self._finish_y_max}]."
        )

    def _elapsed(self) -> float:
        return time.monotonic() - self._start_time

    def _publish_ticking_status(self):
        if self._finished:
            return
        self._status_pub.publish(String(data=f'Time: {self._elapsed():.1f} s'))

    def _on_odom(self, msg: Odometry):
        if self._finished:
            return

        world_x = msg.pose.pose.position.x + self._spawn_x
        world_y = msg.pose.pose.position.y + self._spawn_y

        if world_x >= self._finish_x and  world_y >= self._finish_y_min:
            self._on_finish()

    def _on_finish(self):
        self._finished = True
        self._status_timer.cancel()
        elapsed = self._elapsed()

        self.get_logger().info(f"\033[92mCongratulations! Finished in {elapsed:.2f} s\033[0m")
        self._status_pub.publish(String(data=f'FINISHED! {elapsed:.2f} s'))

        # Give the final status message a moment to actually get bridged
        # and shown before tearing everything down.
        self.create_timer(1.0, self._shutdown_once)

    def _shutdown_once(self):
        self.get_logger().info(
            'Maze finished. Shutting down entire simulation.'
        )

        if rclpy.ok():
            rclpy.shutdown()

        sys.exit(0)

def main(args=None):
    rclpy.init(args=args)
    node = MazeTimerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
