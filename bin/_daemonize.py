"""把一个命令真正脱离父会话启动。

用法:_daemonize.py <log_file> <pid_file> <cmd...>
- start_new_session=True 让子进程进入新会话,父 shell 退出不会 SIGHUP 它
- 所有 fd 关闭,不再绑定到任何 tty
- 把 PID 写到 pid_file(子进程 PID,即 shell 看到的那个)
"""
import os
import shlex
import subprocess
import sys

_, log_file, pid_file, *cmd = sys.argv
if not cmd:
    print("usage: _daemonize.py <log_file> <pid_file> <cmd...>", file=sys.stderr)
    sys.exit(2)

log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)

p = subprocess.Popen(
    cmd,
    start_new_session=True,
    stdin=subprocess.DEVNULL,
    stdout=log_fd,
    stderr=log_fd,
    close_fds=True,
)

with open(pid_file, "w") as f:
    f.write(str(p.pid))
print(f"  PID={p.pid} pgid={os.getpgid(p.pid)} cmd={shlex.join(cmd)}")
