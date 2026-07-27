"""CampusMatch 后台启动器 — 双击运行即可，不依赖终端窗口

用法:
  pythonw bg_server.py        # 静默启动（无窗口）
  python bg_server.py          # 带控制台启动（可看日志）
"""

import subprocess, sys, os, time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log")

cmd = [sys.executable, "app.py"]

with open(LOG_FILE, "w", encoding="utf-8") as log:
    log.write(f"CampusMatch server starting at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log.write(f"PID: {os.getpid()}\n")
    log.flush()

    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.executable.endswith("pythonw.exe") else 0,
    )

    print(f"Server started (PID {proc.pid})")
    print(f"Log: {LOG_FILE}")
    print(f"Access: http://127.0.0.1:5000")
    print("Close this window to stop the server.")

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("Server stopped.")
