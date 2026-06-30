"""Reliably run the browser game and its temporary public tunnel together."""

from __future__ import annotations

import re
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TUNNEL = ROOT / "tools" / "cloudflared.exe"
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def find_open_port() -> int:
    for port in range(8080, 8091):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("Ports 8080 through 8090 are already in use.")


def wait_for_server(port: int, process: subprocess.Popen) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The game server stopped during startup.")
        with socket.socket() as probe:
            probe.settimeout(0.3)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError("The game server did not open its port within 20 seconds.")


def stop(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    if not TUNNEL.exists():
        raise FileNotFoundError(f"Missing tunnel helper: {TUNNEL}")
    port = find_open_port()
    server = None
    tunnel = None
    try:
        print(f"Starting Everdawn Online on local port {port}...", flush=True)
        server = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "browser_server.py",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wait_for_server(port, server)
        print("Game server is ready. Creating the public link...", flush=True)
        tunnel = subprocess.Popen(
            [
                str(TUNNEL),
                "tunnel",
                "--url",
                f"http://127.0.0.1:{port}",
                "--no-autoupdate",
                "--protocol",
                "http2",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        public_url = None
        for line in tunnel.stdout:
            match = URL_PATTERN.search(line)
            if match and public_url is None:
                public_url = match.group(0)
                (ROOT / "PUBLIC_LINK.txt").write_text(public_url, encoding="utf-8")
                print("\n" + "=" * 74)
                print("SEND THIS LINK TO YOUR FRIEND:")
                print(public_url)
                print("=" * 74)
                print("Keep this window open while everyone plays. Press Ctrl+C to stop.\n")
            if tunnel.poll() is not None:
                break
        if public_url is None:
            raise RuntimeError("Cloudflare stopped before creating a public link.")
    except KeyboardInterrupt:
        print("\nStopping the public game...")
    except Exception as error:
        print(f"\nSTARTUP ERROR: {error}")
        input("Press Enter to close...")
    finally:
        stop(tunnel)
        stop(server)


if __name__ == "__main__":
    main()

