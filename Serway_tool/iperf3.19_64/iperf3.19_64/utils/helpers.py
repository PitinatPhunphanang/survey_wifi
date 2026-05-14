"""
utils/helpers.py
General-purpose helper utilities: filename sanitization, subprocess wrappers,
PowerShell helpers, and DB value sanitizer.
"""
import json
import os
import re
import subprocess

import pandas as pd


# =========================
# VALUE PARSERS
# =========================
import re as _re


def parse_float_value(value):
    """Extract a float (including negative) from a string, or return None."""
    if value is None:
        return None
    match = _re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    return float(match.group(0))


def parse_percent_value(value):
    """Extract an integer percentage from a string like '75%', or return None."""
    if not value:
        return None
    match = _re.search(r"(\d+)", str(value))
    if not match:
        return None
    return int(match.group(1))


# =========================
# FILENAME
# =========================
def safe_filename(name: str) -> str:
    """Sanitize a string so it is safe to use as a filename."""
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name.strip())
    return cleaned if cleaned else "wifi_survey"


# =========================
# SUBPROCESS HELPERS
# =========================
def _creation_flags():
    """Return CREATE_NO_WINDOW on Windows to suppress console popups."""
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW
    return 0


def run_command(args, timeout=20):
    """Run a subprocess and return the CompletedProcess result."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=timeout,
        creationflags=_creation_flags(),
    )


def powershell_escape(value):
    """Escape single-quotes for PowerShell string literals."""
    return str(value).replace("'", "''")


def run_powershell_json(script, timeout=20):
    """Run a PowerShell script and return parsed JSON output."""
    result = run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        timeout=timeout,
    )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0 and not stdout:
        raise RuntimeError(stderr or "PowerShell command failed.")
    if not stdout:
        return None

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse PowerShell JSON output: {stdout[:200]}") from exc


# =========================
# DATABASE HELPERS
# =========================
def sanitize_db_value(value):
    """Convert pandas NA/NaN to None for database insertion."""
    if pd.isna(value):
        return None
    return value
