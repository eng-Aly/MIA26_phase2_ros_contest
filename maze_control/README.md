# maze_control

Maze simulation with 3 retractable gate walls (prismatic joints +
`JointPositionController`) for ROS 2 Jazzy + Gazebo Harmonic (gz-sim 8).

## Layout

3 corridors (serpentine), robot starts at ~(0.5, 0.5). Two interior
partitions and the exit doorway are each blocked by a gate. Calling
`/retract_walls` lifts all three gates 0.6 m straight up, clearing the path
to the exit on the east wall.

## Build

```bash
mkdir -p ~/maze_ws/src
cp -r maze_control ~/maze_ws/src/
cd ~/maze_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Run

```bash
ros2 launch maze_control maze_simulation.launch.py
```

To spawn TurtleBot3 instead of the bundled placeholder robot (requires the
`ros_gz`-compatible `turtlebot3_gazebo` package, not the classic-Gazebo one):

```bash
ros2 launch maze_control maze_simulation.launch.py \
  robot_sdf:=/path/to/turtlebot3_gazebo/models/turtlebot3_waffle/model.sdf
```

## Test the gates

```bash
ros2 service call /retract_walls std_srvs/srv/Trigger {}
```

Watch the 3 red/green walls slide up out of the corridors in the Gazebo GUI.

## Sanity-check the bridge directly (bypassing the service)

```bash
ros2 topic pub --once /wall_1/cmd_pos std_msgs/msg/Float64 "data: 0.6"
```

## Run with TurtleBot3 Burger instead

Requires ROBOTIS's ros_gz-ported turtlebot3_simulations (jazzy branch),
built in the same workspace:

```bash
cd ~/training26_ws/src
git clone -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git
# also needed if not already present:
git clone -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3.git
git clone -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3_msgs.git
cd ~/training26_ws
colcon build --symlink-install
source install/setup.bash

ros2 launch maze_control maze_simulation_tb3.launch.py
```

After it spawns, check what topics the Burger's own bundled plugins
actually advertise (naming can drift slightly between forks/versions):

```bash
gz topic -l | grep -i burger
```

`bridge_config.yaml` already bridges plain `/cmd_vel`, `/odom`, and `/tf` -
if Burger's plugins advertise under different names, add matching entries
the same way the gate-wall entries are structured.

## Drive the placeholder robot manually

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}" -r 10
```

## Notes / things to check on your machine

- `gz-sim-joint-position-controller-system` ships with `gz-sim8` (the
  Gazebo Harmonic default install already includes it).
- If gates jitter instead of settling, lower `p_gain`/raise `d_gain` in the
  SDF `<plugin>` blocks, or raise joint `<dynamics><damping>`.
- `ros_gz_bridge`'s `tf2_msgs/msg/TFMessage <-> gz.msgs.Pose_V` bridge entry
  is only needed if you want TF from the bundled `PosePublisher` plugin;
  drop it if you're using a robot with its own localization stack.
