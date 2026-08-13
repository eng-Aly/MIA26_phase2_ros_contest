import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_maze = get_package_share_directory('maze_control')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    pkg_tb3_gazebo = get_package_share_directory('turtlebot3_gazebo')

    world_file = os.path.join(pkg_maze, 'worlds', 'maze_world.sdf')
    bridge_config = os.path.join(pkg_maze, 'config', 'bridge_config.yaml')
    tb3_burger_sdf = os.path.join(
        pkg_tb3_gazebo, 'models', 'turtlebot3_burger', 'model.sdf'
    )

    set_tb3_model = SetEnvironmentVariable('TURTLEBOT3_MODEL', 'burger')

    robot_name_arg = DeclareLaunchArgument('robot_name', default_value='burger')
    x_arg = DeclareLaunchArgument('x', default_value='0.5')
    y_arg = DeclareLaunchArgument('y', default_value='0.5')
    yaw_arg = DeclareLaunchArgument('yaw', default_value='0.0')

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': ['-r ', world_file]}.items(),
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-file', tb3_burger_sdf,
            '-name', LaunchConfiguration('robot_name'),
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', '0.05',
            '-Y', LaunchConfiguration('yaw'),
        ],
        output='screen',
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='maze_bridge',
        parameters=[{'config_file': bridge_config}],
        output='screen',
    )

    wall_service_node = Node(
        package='maze_control',
        executable='wall_retraction_service',
        name='wall_retraction_service',
        output='screen',
    )

    return LaunchDescription([
        set_tb3_model,
        robot_name_arg,
        x_arg,
        y_arg,
        yaw_arg,
        gz_sim,
        spawn_robot,
        bridge,
        wall_service_node,
    ])
