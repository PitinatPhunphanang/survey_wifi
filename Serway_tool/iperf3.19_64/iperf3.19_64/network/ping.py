"""
network/ping.py
Default gateway resolution and ping statistics via PowerShell Test-Connection.
"""
import re

from utils.helpers import run_command, powershell_escape, run_powershell_json
from config import PING_COUNT


# =========================
# GATEWAY
# =========================
def get_default_gateway():
    """Return the lowest-metric default IPv4 gateway from the routing table."""
    try:
        result = run_command(["route", "print", "-4"], timeout=8)
        best_gateway = None
        best_metric = None

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            match = re.match(
                r"^0\.0\.0\.0\s+0\.0\.0\.0\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d+)$",
                line,
            )
            if not match:
                continue

            gateway = match.group(1)
            metric = int(match.group(3))

            if best_metric is None or metric < best_metric:
                best_gateway = gateway
                best_metric = metric

        return best_gateway or "Unknown"
    except Exception:
        return "Unknown"


# =========================
# PING
# =========================
def ping_host(host, count=PING_COUNT):
    """Return (avg_ms, loss_pct) for a simple ping."""
    stats = ping_for_stats(host, count=count)
    return stats["Avg"], stats["Loss_%"]


def ping_for_stats(host, count=10):
    """Return full ping statistics dict: Min, Max, Avg, Loss_%."""
    empty = {"Min": None, "Max": None, "Avg": None, "Loss_%": None}

    if not host or host in ("Unknown", "Timeout", "Unreachable"):
        return empty

    host_escaped = powershell_escape(host)
    script = (
        "$ProgressPreference='SilentlyContinue'; "
        f"$r = Test-Connection -Count {int(count)} -ComputerName '{host_escaped}' -ErrorAction SilentlyContinue | "
        "Select-Object ResponseTime; "
        "if ($r) { $r | ConvertTo-Json -Compress }"
    )

    try:
        data = run_powershell_json(script, timeout=max(10, count * 3))
        if not data:
            return {"Min": None, "Max": None, "Avg": None, "Loss_%": 100}

        if isinstance(data, dict):
            data = [data]

        times = [int(item["ResponseTime"]) for item in data if item.get("ResponseTime") is not None]
        success_count = len(times)
        loss_pct = round(((count - success_count) / count) * 100) if count else None

        if not times:
            return {"Min": None, "Max": None, "Avg": None, "Loss_%": 100}

        return {
            "Min": min(times),
            "Max": max(times),
            "Avg": round(sum(times) / len(times)),
            "Loss_%": loss_pct,
        }
    except Exception:
        return {"Min": None, "Max": None, "Avg": None, "Loss_%": 100}
