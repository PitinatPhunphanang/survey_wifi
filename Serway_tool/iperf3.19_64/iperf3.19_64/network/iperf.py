"""
network/iperf.py
iPerf3 test runner and result parsers (TCP upload/download, UDP jitter/loss).
"""
import json
import os
import subprocess

from utils.helpers import run_command
from config import IPERF_PORT, IPERF_DURATION


# =========================
# IPERF RUNNER
# =========================
def run_iperf(iperf_path, server_ip, args, label):
    """
    Run an iperf3 test and return the parsed JSON result.

    Args:
        iperf_path: Full path to iperf3.exe
        server_ip:  iPerf server IP address
        args:       Extra iperf3 CLI arguments (list)
        label:      Human-readable label for error messages
    """
    if not os.path.exists(iperf_path):
        raise FileNotFoundError(f"iperf3.exe was not found at: {iperf_path}")

    try:
        proc = run_command(
            [iperf_path, "-c", server_ip, "-p", str(IPERF_PORT), "-4"] + args + ["--json"],
            timeout=max(40, IPERF_DURATION + 20),
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode != 0 and not stdout:
            raise RuntimeError(
                f"iPerf3 ({label}) failed.\n"
                f"Command: iperf3.exe -c {server_ip} -p {IPERF_PORT} -4 {' '.join(args)} --json\n"
                f"stderr: {stderr or '-'}"
            )

        if not stdout:
            raise RuntimeError(f"iPerf3 ({label}) returned no data.")

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            preview = stdout[:500]
            raise RuntimeError(
                f"iPerf3 ({label}) returned invalid JSON.\n"
                f"Command: iperf3.exe -c {server_ip} -p {IPERF_PORT} -4 {' '.join(args)} --json\n"
                f"stdout preview: {preview}"
            ) from exc

        if "error" in data:
            raise RuntimeError(f"iPerf3 ({label}): {data['error']}")

        return data

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"iPerf3 ({label}) timed out.") from exc


# =========================
# RESULT PARSERS
# =========================
def parse_iperf_tcp_upload(data):
    """Return TCP upload throughput in Mbps."""
    try:
        return round(data["end"]["sum_sent"]["bits_per_second"] / 1e6, 2)
    except Exception:
        return None


def parse_iperf_tcp_download(data):
    """Return TCP download throughput in Mbps."""
    try:
        return round(data["end"]["sum_received"]["bits_per_second"] / 1e6, 2)
    except Exception:
        return None


def parse_iperf_udp(data):
    """Return (udp_mbps, jitter_ms, loss_pct) from a UDP iperf3 result."""
    udp_mbps = None
    jitter = None
    loss = None

    udp_summary = data.get("end", {}).get("sum_received")
    if not udp_summary:
        udp_summary = data.get("end", {}).get("sum")

    try:
        udp_mbps = round(udp_summary["bits_per_second"] / 1e6, 2)
    except Exception:
        pass

    try:
        jitter = round(udp_summary["jitter_ms"], 2)
    except Exception:
        pass

    try:
        loss = round(udp_summary["lost_percent"], 2)
    except Exception:
        pass

    return udp_mbps, jitter, loss
