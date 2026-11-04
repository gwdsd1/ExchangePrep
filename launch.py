"""Double-click start.cmd; set up an isolated environment and open the local app."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent


def main():
    os.chdir(ROOT)
    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("First launch: preparing Python dependencies. Please wait.", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
    check = subprocess.run([str(python), "-c",
        "import fastapi, uvicorn, pydantic, openai, httpx, bs4, pdfplumber, playwright"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if check.returncode:
        print("Installing missing dependencies. Please wait.", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}/workspace"
    def open_ready():
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(120):
            try:
                with opener.open(url, timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(url)
                        return
            except OSError:
                time.sleep(0.5)
    threading.Thread(target=open_ready, daemon=True).start()
    print(f"Opening {url}\nKeep this window open. Ctrl+C stops the service.", flush=True)
    subprocess.run([str(python), "-m", "uvicorn", "app:app", "--host", "127.0.0.1",
                    "--port", str(port)], check=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Startup failed: {exc}\nCheck Python 3.11+ and your network, then retry.")
        sys.exit(1)
