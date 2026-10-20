"""Temporary identity TFs for an explicitly selected stationary preview only."""
import signal
import os
import subprocess
import time


def commands(params_file=None):
    common = ['ros2', 'run', 'tf2_ros', 'static_transform_publisher',
              '--x', '0', '--y', '0', '--z', '0', '--roll', '0', '--pitch', '0', '--yaw', '0']
    return [common + ['--frame-id', 'odom', '--child-frame-id', 'base_footprint'],
            common + ['--frame-id', 'base_footprint', '--child-frame-id', 'laser'],
            ['ros2', 'launch', 'slam_toolbox', 'online_async_launch.py', 'use_sim_time:=false'] +
            (['slam_params_file:='+str(params_file)] if params_file else [])]


def run(popen=subprocess.Popen, command_list=None):
    children = []
    stopping = False
    def stop(signum, frame):
        nonlocal stopping
        stopping = True
    original = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        for command in (commands() if command_list is None else command_list):
            if stopping:
                break
            children.append(popen(command, start_new_session=True))
        while not stopping and all(p.poll() is None for p in children):
            time.sleep(.1)
        if not stopping:
            return next((p.returncode or 1 for p in children if p.poll() is not None), 1)
        return 0
    finally:
        for process in children:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + 2
        for process in children:
            try:
                process.wait(timeout=max(.01, deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=1)
        for sig, handler in original.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    from slam_runtime import parameters
    with parameters() as path:
        raise SystemExit(run(command_list=commands(path)))
