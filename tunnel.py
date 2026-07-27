"""CampusMatch 公网隧道管理器

用法:
  python tunnel.py              # 启动 serveo 隧道，自动获取公网 URL
  python tunnel.py --url-only   # 只打印当前公网 URL
"""

import subprocess, sys, os, re, time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
URL_FILE = os.path.join(os.path.dirname(__file__), ".public_url")


def start_tunnel():
    """启动 serveo SSH 隧道，提取公网 URL 并写入文件"""
    print("[tunnel] Starting serveo tunnel...")

    cmd = [
        "ssh", "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=30",
        "-o", "TCPKeepAlive=yes",
        "-R", "80:localhost:5000",
        "serveo.net",
    ]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )

    url = None
    for line in proc.stdout:
        line = line.strip()
        print(f"  {line}")
        # serveo prints: Forwarding HTTP traffic from https://xxx.serveousercontent.com
        m = re.search(r"https://([a-z0-9\-]+)\.serveo(?:usercontent)?\.com", line)
        if m:
            url = f"https://{m.group(1)}.serveousercontent.com"
            with open(URL_FILE, "w") as f:
                f.write(url)
            print(f"\n[tunnel] PUBLIC URL: {url}")
            print(f"[tunnel] URL saved to {URL_FILE}")
            print(f"[tunnel] Share this link with users!\n")
            # Don't break — keep SSH alive
        time.sleep(0.1)

    print(f"[tunnel] Connection closed. Exit code: {proc.returncode}")
    return url


def get_url():
    """读取已保存的公网 URL"""
    if os.path.exists(URL_FILE):
        with open(URL_FILE) as f:
            return f.read().strip()
    return None


if __name__ == "__main__":
    if "--url-only" in sys.argv:
        url = get_url()
        if url:
            print(url)
        else:
            print("No public URL found. Run 'python tunnel.py' first.")
            sys.exit(1)
    else:
        print("CampusMatch Tunnel Manager")
        print("Keep this window open to maintain the public URL.")
        print("Press Ctrl+C to stop.\n")
        start_tunnel()
