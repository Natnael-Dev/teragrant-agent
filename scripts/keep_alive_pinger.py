#!/usr/bin/env python3
"""
TeraGrant Keep-Alive Heartbeat Daemon.
Periodically pings the deployed Render instance to prevent sleeping on free-tier inactivity timeouts.
"""

import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

TARGET_URL = "https://teragrant-agent.onrender.com/healthz"
DEFAULT_INTERVAL_SECONDS = 600  # 10 minutes (Render sleeps after 15 minutes)


def ping(url: str = TARGET_URL) -> bool:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "TeraGrant-KeepAlive-Pinger/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.getcode()
            print(f"[{timestamp}] Heartbeat to {url} -> HTTP {code} OK (Active)")
            return code == 200
    except urllib.error.HTTPError as e:
        print(f"[{timestamp}] Heartbeat error -> HTTP {e.code}: {e.reason}")
        return False
    except Exception as ex:
        print(f"[{timestamp}] Heartbeat connection failed -> {ex}")
        return False


def run_loop(interval: int = DEFAULT_INTERVAL_SECONDS):
    print(f"Starting TeraGrant Keep-Alive Daemon...")
    print(f"Target URL: {TARGET_URL}")
    print(f"Interval: Every {interval} seconds ({interval // 60} minutes)")
    print("Press Ctrl+C to stop.\n")

    while True:
        ping()
        time.sleep(interval)


if __name__ == "__main__":
    interval_sec = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INTERVAL_SECONDS
    run_loop(interval_sec)
