import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
    Shutdown,
)
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_maze = get_package_share_directory('maze_control')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Requires ROBOTIS's ros_gz-ported turtlebot3_simulations, jazzy branch:
    #   cd ~/training26_ws/src
    #   git clone -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git
    # (also needs the 'turtlebot3' and 'turtlebot3_msgs' packages present)
    pkg_tb3_gazebo = get_package_share_directory('turtlebot3_gazebo')

    world_file = os.path.join(pkg_maze, 'worlds', 'maze_world.sdf')
    bridge_config = os.path.join(pkg_maze, 'config', 'bridge_config.yaml')
    default_gui_config = os.path.join(pkg_maze, 'config', 'gui.config')
    tb3_burger_sdf = os.path.join(
        pkg_tb3_gazebo, 'models', 'turtlebot3_burger', 'model.sdf'
    )

    gui_config_arg = DeclareLaunchArgument(
        'gui_config',
        default_value=default_gui_config,
        description='Path to a saved gz-gui client config (docks the timer panel top-left).',
    )

    # Some turtlebot3_gazebo launch/description files key off this env var
    # even when we spawn the model.sdf directly ourselves - set it so any
    # included robot_state_publisher / description logic stays consistent.
    set_tb3_model = SetEnvironmentVariable('TURTLEBOT3_MODEL', 'burger')

    robot_name_arg = DeclareLaunchArgument('robot_name', default_value='burger')
    x_arg = DeclareLaunchArgument('x', default_value='0.5')
    y_arg = DeclareLaunchArgument('y', default_value='0.5')
    yaw_arg = DeclareLaunchArgument('yaw', default_value='0.0')

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': [
                '-r ', world_file,
                ' --gui-config ', LaunchConfiguration('gui_config'),
            ],
        }.items(),
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

    timer_node = Node(
        package='maze_control',
        executable='maze_timer_node',
        name='maze_timer_node',
        output='screen',
        parameters=[{
            'spawn_x': ParameterValue(LaunchConfiguration('x'), value_type=float),
            'spawn_y': ParameterValue(LaunchConfiguration('y'), value_type=float),
        }],
    )

    # --- Cleanup chain on finish ---------------------------------------------
    # gz-sim's ruby launcher wrapper doesn't reliably forward SIGINT/SIGTERM
    # to its own child processes (confirmed: `ps -a` shows extra `ruby` PIDs
    # launch never tracked), so a plain Shutdown() alone leaves gz-sim
    # running. Force-kill it instead.
    #
    # Tried matching the exact `gz sim ...` command line first (-f with the
    # full path) - it only caught the top-level wrapper process, not the
    # server/GUI children, which apparently run under `ruby` with a
    # different full command line. Matching on process name alone (no -f)
    # is what actually clears all of them - confirmed empirically. This is
    # blunt: it will kill ANY ruby process on the machine, not just gz-sim's,
    # so if you're ever running other ruby tooling alongside this, that's
    # the tradeoff. Narrow it back to a -f pattern if that becomes a problem
    # - just verify with `ps -a` after a run that it still catches everything.
    #
    # IMPORTANT: this pkill step and Shutdown() must NOT be in the same
    # on_exit list. Shutdown() broadcasts SIGINT to every process currently
    # running in the launch tree - including a pkill ExecuteProcess started
    # moments earlier in the same list - and can kill it before it finishes
    # running. Chaining via a second OnProcessExit, keyed to the pkill
    # process itself, guarantees Shutdown() only fires after pkill is done.

    congrats_msg = ExecuteProcess(
        cmd=[
        'bash',
        '-c',
        'echo -e "\\033[92mCongratulations! Maze completed successfully.\\033[0m"'
        ],
        output='screen',
    )

    kill_gazebo = ExecuteProcess(
        cmd=['pkill', '-9', 'ruby'],
        output='screen',
    )

    on_finish = RegisterEventHandler(
        OnProcessExit(
            target_action=timer_node,
            on_exit=[congrats_msg, kill_gazebo],
        )
    )

    shutdown_after_kill = RegisterEventHandler(
        OnProcessExit(
            target_action=kill_gazebo,
            on_exit=[Shutdown(reason='Maze finished, gz-sim force-killed')],
        )
    )

    # Safety net for any OTHER shutdown path too (e.g. plain Ctrl+C on the
    # launch terminal), not just the finish-triggered one above.
    force_kill_on_any_shutdown = RegisterEventHandler(
        OnShutdown(
            on_shutdown=[
                ExecuteProcess(
                    cmd=['pkill', '-9', 'ruby'],
                    output='screen',
                )
            ]
        )
    )

    return LaunchDescription([
        gui_config_arg,
        set_tb3_model,
        robot_name_arg,
        x_arg,
        y_arg,
        yaw_arg,
        gz_sim,
        spawn_robot,
        bridge,
        wall_service_node,
        timer_node,
        on_finish,
        shutdown_after_kill,
        force_kill_on_any_shutdown,
    ])