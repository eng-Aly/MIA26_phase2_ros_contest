import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_maze = get_package_share_directory('maze_control')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_file = os.path.join(pkg_maze, 'worlds', 'maze_world.sdf')
    bridge_config = os.path.join(pkg_maze, 'config', 'bridge_config.yaml')
    default_robot_sdf = os.path.join(pkg_maze, 'models', 'simple_robot', 'model.sdf')

    # --- Launch arguments ---------------------------------------------------
    robot_sdf_arg = DeclareLaunchArgument(
        'robot_sdf',
        default_value=default_robot_sdf,
        description=(
            'Path to the robot SDF to spawn. Defaults to the bundled '
            'placeholder diff-drive robot. To spawn TurtleBot3 instead, '
            'point this at your turtlebot3_gazebo model, e.g.: '
            '$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/'
            'models/turtlebot3_waffle/model.sdf'
        ),
    )
    robot_name_arg = DeclareLaunchArgument('robot_name', default_value='robot')
    x_arg = DeclareLaunchArgument('x', default_value='0.5')
    y_arg = DeclareLaunchArgument('y', default_value='0.5')
    yaw_arg = DeclareLaunchArgument('yaw', default_value='0.0')
    gui_arg = DeclareLaunchArgument('gui', default_value='true')

    # --- Gazebo ---------------------------------------------------------------
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': ['-r ', world_file],
        }.items(),
    )

    # --- Spawn robot ------------------------------------------------------
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-file', LaunchConfiguration('robot_sdf'),
            '-name', LaunchConfiguration('robot_name'),
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', '0.05',
            '-Y', LaunchConfiguration('yaw'),
        ],
        output='screen',
    )

    # --- ROS <-> GZ bridge --------------------------------------------------
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='maze_bridge',
        parameters=[{'config_file': bridge_config}],
        output='screen',
    )

    # --- Trigger service node -----------------------------------------------
    wall_service_node = Node(
        package='maze_control',
        executable='wall_retraction_service',
        name='wall_retraction_service',
        output='screen',
    )

    return LaunchDescription([
        robot_sdf_arg,
        robot_name_arg,
        x_arg,
        y_arg,
        yaw_arg,
        gui_arg,
        gz_sim,
        spawn_robot,
        bridge,
        wall_service_node,
    ])
